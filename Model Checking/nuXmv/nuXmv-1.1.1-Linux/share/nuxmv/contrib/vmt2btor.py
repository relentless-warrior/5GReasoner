#!/usr/bin/env python

"""
Convert an SMT2 transition system (init, trans, prop) into a BTOR model
"""

import os, sys
from mathsat import *
import vmt2nuxmv
import optparse, math, time

Unsupported = vmt2nuxmv.Unsupported


def to_btor(env, model, out):
    # first, check that there are only bvs and arrays
    lines = []
    pr = lines.append

    def fix_name(name):
        name = name.replace(' ', '_').replace(';', '_')
        return name

    btorid = [1]
    def getid():
        btorid[0] += 1
        return btorid[0]

    def gettp(tp):
        if msat_is_bool_type(env, tp):
            return (1,)
        elif msat_is_bv_type(env, tp):
            _, w = msat_is_bv_type(env, tp)
            return (w,)
        elif msat_is_array_type(env, tp):
            _, iw, ew = msat_is_array_type(env, tp)
            return (ew, iw)
        else:
            raise Unsupported("unsupported type: %s" % msat_type_repr(tp))

    allnames = set()
    def declare_var(d, name):
        tp = gettp(msat_decl_get_return_type(d))
        if len(tp) == 1:
            t = 'var %d' % tp[0]
        else:
            t = 'avar %d %d' % tp
        i = getid()
        pr('%d %s %s\n' % (i, t, fix_name(name)))
        allnames.add(name)
        return i

    def mkname(name):
        bn = name
        i = 1
        while name in allnames:
            name = '%s.%d' % (bn, i)
            i += 1
        return name

    pr('1 constd 1 1\n')

    cache = {
        msat_make_true(env) : 1,
        msat_make_false(env) : -1,
        }
    
    for name in model.ivars:
        d = msat_find_decl(env, name)
        v = msat_make_constant(env, d)
        cache[v] = declare_var(d, name)
        
    for name in model.svars:
        d = msat_find_decl(env, name)
        if MSAT_ERROR_DECL(d):
            nn = model.next[name]
            dd = msat_find_decl(env, nn)
            assert not MSAT_ERROR_DECL(dd)
            d = msat_declare_function(env, name, msat_decl_get_return_type(dd))
        v = msat_make_constant(env, d)
        cur = declare_var(d, name)
        cache[v] = cur
        d = msat_find_decl(env, model.next[name])
        if MSAT_ERROR_DECL(d):
            nn = model.next[name]
            d = msat_declare_function(env, nn, msat_term_get_type(v))
        v = msat_make_constant(env, d)
        next = declare_var(d, mkname('next(' + fix_name(name) + ')'))
        cache[v] = next
        tp = gettp(msat_decl_get_return_type(d))
        if len(tp) == 1:
            nexttp = 'next %d' % tp[0]
        else:
            nexttp = 'anext %d %d' % tp
        pr('%d %s %d %d\n' % (getid(), nexttp, cur, next))

    def unsupported(op):
        def f(a):
            raise Unsupported(op)
        return f

    def tag_ite(t, a):
        tp = gettp(msat_term_get_type(msat_term_get_arg(t, 1)))
        if len(tp) == 2:
            name = 'acond'
        else:
            name = 'cond'
        return (name,) + a

    def tag_extract(t, a):
        ok, l, h = msat_term_is_bv_extract(env, t)
        assert ok
        func = lambda a: ('slice', a[0], h, l)

    def tag_log2_op(op):
        def f(t, a):
            w = gettp(msat_term_get_type(msat_term_get_arg(t, 0)))[0]
            n = math.log(w, 2)
            n2 = int(math.ceil(n))
            if n2 > n:
                ww = 2**n2
                i = getid()
                pr('%d constd %d 0\n' % (i, (ww-w)))
                ii = getid()
                pr('%d concat %d %d %d\n' % (ii, ww, i, a[0]))
                a[0] = ii
                w = ww
            i = getid()
            pr('%d slice %d %d %d 0\n' % (i, n2, a[1], n2-1))
            a[1] = i
            if n2 > n:
                i = getid()
                pr('%d %s %d %d %d\n' % (i, op, 2**n2, a[0], a[1]))
                return ('slice', i, w-1, 0)
            else:
                return (op, a[0], a[1])
        return f

    def tag_zext(t, a):
        _, ww = msat_term_is_bv_zext(env, t)
        i = getid()
        pr('%d constd %d 0\n' % (i, ww))
        return ('concat', i, a[0])

    def tag_sext(t, a):
        _, ww = msat_term_is_bv_sext(env, t)
        i0 = getid()
        pr('%d constd %d 0\n' % (i0, ww))
        i1 = getid()
        pr('%d slice 1 %d 1 0\n' % (i1, a[0]))
        i2 = getid()
        pr('%d cond %d %d -%d %d\n' % (i2, ww, i1, i0, i0))
        return ('concat', i2, a[0])

    tagmap = {
        MSAT_TAG_AND: lambda t, a: ('and', a[0], a[1]),
        MSAT_TAG_OR: lambda t, a: ('or', a[0], a[1]),
        MSAT_TAG_NOT: lambda t, a: ('not', a[0]),
        MSAT_TAG_IFF: lambda t, a: ('eq', a[0], a[1]),
        MSAT_TAG_PLUS: unsupported("+"),
        MSAT_TAG_TIMES: unsupported("*"),
        MSAT_TAG_FLOOR: unsupported("floor"),
        MSAT_TAG_LEQ: unsupported("<="),
        MSAT_TAG_EQ: lambda t, a: ('eq', a[0], a[1]),
        MSAT_TAG_ITE: tag_ite,
        MSAT_TAG_INT_MOD_CONGR: unsupported("int mod congr"),
        MSAT_TAG_BV_CONCAT: lambda t, a: ('concat', a[0], a[1]),
        MSAT_TAG_BV_EXTRACT: tag_extract,
        MSAT_TAG_BV_NOT: lambda t, a: ('not', a[0]),
        MSAT_TAG_BV_AND: lambda t, a: ('and', a[0], a[1]),
        MSAT_TAG_BV_OR: lambda t, a: ('or', a[0], a[1]),
        MSAT_TAG_BV_XOR: lambda t, a: ('xor', a[0], a[1]),
        MSAT_TAG_BV_ULT: lambda t, a: ('ult', a[0], a[1]),
        MSAT_TAG_BV_SLT: lambda t, a: ('slt', a[0], a[1]),
        MSAT_TAG_BV_ULE: lambda t, a: ('ulte', a[0], a[1]),
        MSAT_TAG_BV_SLE: lambda t, a: ('slte', a[0], a[1]),
        MSAT_TAG_BV_COMP: lambda t, a: ('eq', a[0], a[1]),
        MSAT_TAG_BV_NEG: lambda t, a: ('neg', a[0]),
        MSAT_TAG_BV_ADD: lambda t, a: ('add', a[0], a[1]),
        MSAT_TAG_BV_SUB: lambda t, a: ('sub', a[0], a[1]),
        MSAT_TAG_BV_MUL: lambda t, a: ('mul', a[0], a[1]),
        MSAT_TAG_BV_UDIV: lambda t, a: ('udiv', a[0], a[1]),
        MSAT_TAG_BV_SDIV: lambda t, a: ('sdiv', a[0], a[1]),
        MSAT_TAG_BV_UREM: lambda t, a: ('urem', a[0], a[1]),
        MSAT_TAG_BV_SREM: lambda t, a: ('srem', a[0], a[1]),
        MSAT_TAG_BV_LSHL: tag_log2_op('sll'),
        MSAT_TAG_BV_LSHR: tag_log2_op('srl'),
        MSAT_TAG_BV_ASHR: tag_log2_op('sra'),
        MSAT_TAG_BV_ROL: tag_log2_op('rol'),
        MSAT_TAG_BV_ROR: tag_log2_op('ror'),
        MSAT_TAG_BV_ZEXT: tag_zext,
        MSAT_TAG_BV_SEXT: tag_sext,
        MSAT_TAG_ARRAY_READ: lambda t, a: ('read', a[0], a[1]),
        MSAT_TAG_ARRAY_WRITE: lambda t, a: ('write', a[0], a[1], a[2]),
        MSAT_TAG_FP_EQ: unsupported("fp eq"),
        MSAT_TAG_FP_LT: unsupported("fp lt"),
        MSAT_TAG_FP_LE: unsupported("fp le"),
        MSAT_TAG_FP_NEG: unsupported("fp neg"),
        MSAT_TAG_FP_ADD: unsupported("fp add"),
        MSAT_TAG_FP_SUB: unsupported("fp sub"),
        MSAT_TAG_FP_MUL: unsupported("fp mul"),
        MSAT_TAG_FP_DIV: unsupported("fp div"),
        MSAT_TAG_FP_CAST: unsupported("fp cast"),
        MSAT_TAG_FP_FROM_SBV: unsupported("fp from sbv"),
        MSAT_TAG_FP_FROM_UBV: unsupported("fp from ubv"),
        MSAT_TAG_FP_TO_BV: unsupported("fp to bv"),
        MSAT_TAG_FP_AS_IEEEBV: unsupported("fp as ieeebv"),
        MSAT_TAG_FP_ISNAN: unsupported("fp isnan"),
        MSAT_TAG_FP_ISINF: unsupported("fp isinf"),
        MSAT_TAG_FP_ISZERO: unsupported("fp iszero"),
        MSAT_TAG_FP_ISSUBNORMAL: unsupported("fp issubnormal"),
        MSAT_TAG_FP_FROM_IEEEBV: unsupported("fp from ieeebv"),
        }
        

    def translate(term):
        def visit(e, t, pre):
            if t in cache:
                return MSAT_VISIT_SKIP
            if not pre:
                args = [cache[msat_term_get_arg(t, i)]
                        for i in range(msat_term_arity(t))]

                if msat_term_is_number(e, t):
                    val = msat_term_to_number(e, t)
                    ok, w = msat_is_bv_type(e, msat_term_get_type(t))
                    if ok:
                        i = getid()
                        pr('%d constd %d %s\n' % (i, w, val))
                        val = i
                    else:
                        raise Unsupported("unsupported type: %s" %
                                          msat_type_repr(msat_term_get_type(t)))
                    cache[t] = val

                else:
                    tag = msat_decl_get_tag(env, msat_term_get_decl(t))
                    func = tagmap.get(tag, unsupported)

                    val = func(t, args)
                    idx = getid()
                    tp = gettp(msat_term_get_type(t))
                    pr('%d %s %s %s\n' % (idx, val[0],
                                          ' '.join(map(str, tp)),
                                          ' '.join(map(str, val[1:]))))
                    cache[t] = idx
                
            return MSAT_VISIT_PROCESS
        
        msat_visit_term(env, term, visit)

    rcache = {}
    def visit_repl(e, t, pre):
        if not pre:
            d = msat_term_get_decl(t)
            name = msat_decl_get_name(d)
            if name in model.next:
                dd = msat_find_decl(env, model.next[name])                
                tt = msat_make_constant(env, dd)
            else:
                tt = msat_make_term(env, d,
                                    [rcache[msat_term_get_arg(t, i)]
                                     for i in range(msat_term_arity(t))])
            rcache[t] = tt
        return MSAT_VISIT_PROCESS
    msat_visit_term(env, model.init, visit_repl)

    tinit = rcache[model.init]
    pr('; init\n')
    translate(tinit)
    pr('; trans\n')
    translate(model.trans)

    pr('; reset sequence\n')
    reset0 = getid()
    pr('%d var 1 %s\n' % (reset0, mkname("model-reset0")))
    pr('%d next 1 %d 1\n' % (getid(), reset0))
    reset1 = getid()
    pr('%d var 1 %s\n' % (reset1, mkname("model-reset1")))
    pr('%d next 1 %d %d\n' % (getid(), reset1, reset0))
    first = getid()
    pr('%d and 1 %d -%d\n' % (first, reset0, reset1))    

    pr('; model var\n')
    modelvar = getid()
    pr('%d var 1 %s\n' % (modelvar, mkname("model-valid")))
    modelval = getid()
    init = cache[tinit]
    trans = cache[model.trans]
    step = getid()
    pr('%d and 1 %d %d\n' % (step, modelvar, trans))
    pr('%d cond 1 %d %d %d\n' % (modelval, first, init, step))
    ok = getid()
    pr('%d cond 1 %d %d -1\n' % (ok, reset0, modelval))
    pr('%d next 1 %d %d\n' % (getid(), modelvar, ok))

    if model.invarprops:
        pr('; property\n')
        translate(model.invarprops[0])
        p = cache[model.invarprops[0]]
        r = getid()
        pr('%d and 1 %d -%d\n' % (r, modelvar, p))
        pr('%d root 1 %d\n' % (getid(), r))

    write = sys.stdout.write
    write('; generated by %s on %s\n' %
          (os.path.basename(sys.argv[0]), time.ctime()))
    for line in lines:
        write(line)
    

def main():
    parser = optparse.OptionParser('''\
%prog [SOURCE or stdin]

If SOURCE is a dir, it is expected to contain a benchmark in the format
(init.smt2, trans.smt2, property.smt2). If SOURCE is a file, it is expected
to be in "vmt2" format.

Output goes to stdout.\
''')
    parser.add_option('-p', '--prop', type='int',
                      help='index of the invar property to dump (0 by default)')
    
    opts, args = parser.parse_args()
    if len(args) > 1:
        parser.print_help()
        exit(0)
    elif len(args) == 1:
        src = args[0]
    else:
        src = sys.stdin
        
    env = msat_create_env()

    model = vmt2nuxmv.getmodel(env, src)
    if opts.prop is not None:
        if opts.prop < 0 or opts.prop > len(model.invarprops):
            sys.stderr.write('ERROR, invalid property index %d\n' % opts.prop)
        model.invarprops = [model.invarprops[opts.prop]]
    try:
        to_btor(env, model, sys.stdout)
    except Unsupported as e:
        sys.stderr.write("ERROR: unsupported operation: %s\n" % e.op)
    msat_destroy_env(env)


if __name__ == '__main__':
    main()
