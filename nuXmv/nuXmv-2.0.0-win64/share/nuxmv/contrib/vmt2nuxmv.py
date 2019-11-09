#!/usr/bin/env python

"""
Convert an SMT2 transition system (init, trans, prop) into a NuSMV model
"""

from mathsat import *
import os, sys
import optparse
from email.utils import quote
import time


class Model(object):
    def __init__(self):
        self.init = None
        self.trans = None
        self.invarprops = []
        self.liveprops = []
        self.svars = set()
        self.ivars = set()
        self.next = {}
        self.cur = {}

# end of class Model


def getmodel_dir(env, d):
    with open(os.path.join(d, 'init.smt2')) as src:
        init = msat_from_smtlib2(env, src.read())
    with open(os.path.join(d, 'trans.smt2')) as src:
        trans = msat_from_smtlib2(env, src.read())
    with open(os.path.join(d, 'property.smt2')) as src:
        prop = msat_from_smtlib2(env, src.read())

    return getmodel_formulas(env, init, trans, prop)


def getmodel_formulas(env, init, trans, prop):
    svars = set()
    ivars = set()
    next = {}
    cur = {}

    def visit(e, t, pre):
        if pre:
            if msat_term_is_constant(e, t):
                n = msat_decl_get_name(msat_term_get_decl(t))
                if n.endswith('.next'):
                    cn = n[:-5]
                    svars.add(cn)
                    next[cn] = n
                    cur[n] = cn
                else:
                    ivars.add(n)
        return MSAT_VISIT_PROCESS

    msat_visit_term(env, init, visit)
    msat_visit_term(env, trans, visit)
    msat_visit_term(env, prop, visit)

    ivars -= svars

    ret = Model()
    ret.init = init
    ret.trans = trans
    ret.invarprops.append(prop)
    ret.svars = svars
    ret.ivars = ivars
    ret.next = next
    ret.cur = cur

    return ret


def getmodel_vmt2(env, name):
    if hasattr(name, 'read'):
        data = name.read()
    else:
        with open(name) as src:
            data = src.read()
    r = msat_annotated_list_from_smtlib2(env, data)
    if r is None:
        raise Exception("error: %s" % msat_last_error_message(env))
    terms, annots = r

    ret = Model()
    ret.init = msat_make_true(env)
    ret.trans = msat_make_true(env)
    invarprops = []
    liveprops = []

    def unquote(v):
        if v.startswith('|'):
            assert v.endswith('|')
            return v[1:-1]
        return v

    for i, t in enumerate(terms):
        key = annots[2*i]
        val = annots[2*i+1]

        if key == "init":
            ret.init = msat_make_and(env, ret.init, t)
        elif key == "trans":
            ret.trans = msat_make_and(env, ret.trans, t)
        elif key == "invar-property":
            idx = int(val)
            invarprops.append((t, idx))
        elif key == "live-property":
            idx = int(val)
            liveprops.append((t, idx))            
        elif key == "next":
            val = unquote(val)
            d = msat_term_get_decl(t)
            cn = msat_decl_get_name(d)
            ret.svars.add(cn)
            ret.next[cn] = val
            ret.cur[val] = cn

    def visit(e, t, pre):
        if pre:
            if msat_term_is_constant(e, t):
                n = msat_decl_get_name(msat_term_get_decl(t))
                if n not in ret.svars and n not in ret.cur:
                    ret.ivars.add(n)
        return MSAT_VISIT_PROCESS
    
    msat_visit_term(env, ret.init, visit)
    msat_visit_term(env, ret.trans, visit)
    for p in invarprops:
        msat_visit_term(env, p[0], visit)
    for p in liveprops:
        msat_visit_term(env, p[0], visit)

    ret.invarprops = [p[0] for p in sorted(invarprops, key=lambda (t, i): i)]
    ret.liveprops = [p[0] for p in sorted(liveprops, key=lambda (t, i): i)]

    return ret


def getmodel(env, name_or_file):
    if hasattr(name_or_file, 'read'):
        model = getmodel_vmt2(env, name_or_file)
    if os.path.isdir(name_or_file):
        model = getmodel_dir(env, name_or_file)
    else:
        model = getmodel_vmt2(env, name_or_file)
        
    for name in model.svars:
        d = msat_find_decl(env, name)
        if MSAT_ERROR_DECL(d):
            nn = model.next[name]
            dd = msat_find_decl(env, nn)
            assert not MSAT_ERROR_DECL(dd)
            d = msat_declare_function(env, name, msat_decl_get_return_type(dd))
        d = msat_find_decl(env, model.next[name])
        if MSAT_ERROR_DECL(d):
            nn = model.next[name]
            d = msat_declare_function(env, nn, msat_term_get_type(v))
        
    return model


class Unsupported(Exception):
    def __init__(self, op):
        super(Unsupported, self).__init__(op)
        self.op = op


def to_nuxmv(env, model, out):
    pr = out.write

    def fix_name(name):
        name = '"%s"' % quote(name)
        return name

    def type_recur(tp):
        if msat_is_bool_type(env, tp):
            t = 'boolean'
        elif msat_is_rational_type(env, tp):
            t = 'real'
        elif msat_is_integer_type(env, tp):
            t = 'integer'
        else:
            ok, w = msat_is_bv_type(env, tp)
            if ok:
                t = 'word[%d]' % w
            else:
                ok, itp, etp = msat_is_array_type(env, tp)
                if ok:
                    idx = type_recur(itp)
                    elem = type_recur(etp)
                    t = 'array %s of %s' % (idx, elem)
                else:
                    assert False
        return t 
        
    def declare_var(name):
        d = msat_find_decl(env, name)
        tp = msat_decl_get_return_type(d)
        pr('%s : %s;\n' % (fix_name(name), type_recur(tp)))


    cache = {
        msat_make_true(env) : 'TRUE',
        msat_make_false(env) : 'FALSE',
        }
    for name in model.ivars:
        d = msat_find_decl(env, name)
        assert not MSAT_ERROR_DECL(d)
        v = msat_make_constant(env, d)
        cache[v] = fix_name(name)
    for name in model.svars:
        d = msat_find_decl(env, name)
        assert not MSAT_ERROR_DECL(d)
        v = msat_make_constant(env, d)
        cache[v] = fix_name(name)
        d = msat_find_decl(env, model.next[name])
        assert not MSAT_ERROR_DECL(d)
        v = msat_make_constant(env, d)
        cache[v] = 'next(' + fix_name(name) + ')'

    defn = [1]
    defs = []

    def unsupported(op):
        def f(a):
            raise Unsupported(op)
        return f
    special = object()
    
    tagmap = {
        MSAT_TAG_TRUE: lambda a: 'TRUE',
        MSAT_TAG_FALSE: lambda a: 'FALSE',
        MSAT_TAG_AND: lambda a: '%s & %s' % (a[0], a[1]),
        MSAT_TAG_OR: lambda a: '%s | %s' % (a[0], a[1]),
        MSAT_TAG_NOT: lambda a: '! %s' % a[0],
        MSAT_TAG_IFF: lambda a: '%s <-> %s' % (a[0], a[1]),
        MSAT_TAG_PLUS: lambda a: '%s + %s' % (a[0], a[1]),
        MSAT_TAG_TIMES: lambda a: '%s * %s' % (a[0], a[1]),
        MSAT_TAG_FLOOR: unsupported("floor"),
        MSAT_TAG_LEQ: lambda a: '%s <= %s' % (a[0], a[1]),
        MSAT_TAG_EQ: lambda a: '%s = %s' % (a[0], a[1]),
        MSAT_TAG_ITE: lambda a: '(case %s: %s; TRUE: %s; esac)' % (a[0], a[1],
                                                                   a[2]),
        MSAT_TAG_INT_MOD_CONGR: unsupported("int mod congr"),
        MSAT_TAG_BV_CONCAT: lambda a: '%s :: %s' % (a[0], a[1]),
        MSAT_TAG_BV_EXTRACT: special,
        MSAT_TAG_BV_NOT: lambda a: '! %s' % a[0],
        MSAT_TAG_BV_AND: lambda a: '%s & %s' % (a[0], a[1]),
        MSAT_TAG_BV_OR: lambda a: '%s | %s' % (a[0], a[1]),
        MSAT_TAG_BV_XOR: lambda a: '%s xor %s' % (a[0], a[1]),
        MSAT_TAG_BV_ULT: lambda a: '%s < %s' % (a[0], a[1]),
        MSAT_TAG_BV_SLT: lambda a: 'signed(%s) < signed(%s)' % (a[0], a[1]),
        MSAT_TAG_BV_ULE: lambda a: '%s <= %s' % (a[0], a[1]),
        MSAT_TAG_BV_SLE: lambda a: 'signed(%s) <= signed(%s)' % (a[0], a[1]),
        MSAT_TAG_BV_COMP: lambda a: 'word1(%s = %s)' % (a[0], a[1]),
        MSAT_TAG_BV_NEG: lambda a: '- %s' % a[0],
        MSAT_TAG_BV_ADD: lambda a: '%s + %s' % (a[0], a[1]),
        MSAT_TAG_BV_SUB: lambda a: '%s - %s' % (a[0], a[1]),
        MSAT_TAG_BV_MUL: lambda a: '%s * %s' % (a[0], a[1]),
        MSAT_TAG_BV_UDIV: lambda a: '%s / %s' % (a[0], a[1]),
        MSAT_TAG_BV_SDIV:
        lambda a: 'unsigned(signed(%s) / signed(%s))' % (a[0], a[1]),
        MSAT_TAG_BV_UREM: lambda a: '%s mod %s' % (a[0], a[1]),
        MSAT_TAG_BV_SREM:
        lambda a: 'unsigned(signed(%s) mod signed(%s))' % (a[0], a[1]),
        MSAT_TAG_BV_LSHL: lambda a: '%s << %s' % (a[0], a[1]),
        MSAT_TAG_BV_LSHR: lambda a: '%s >> %s' % (a[0], a[1]),
        MSAT_TAG_BV_ASHR: lambda a: 'unsigned(signed(%s) >> %s)' % (a[0], a[1]),
        MSAT_TAG_BV_ROL: unsupported("bv rol"),
        MSAT_TAG_BV_ROR: unsupported("bv ror"),
        MSAT_TAG_BV_ZEXT: special,
        MSAT_TAG_BV_SEXT: special,
        MSAT_TAG_ARRAY_READ: lambda a: 'READ(%s, %s)' % (a[0], a[1]),
        MSAT_TAG_ARRAY_WRITE: lambda a: 'WRITE(%s, %s, %s)' % (a[0], a[1], a[2]),
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
                        val = '0ud%d_%s' % (w, val)
                    else:
                        val = str(val)
                    cache[t] = val

                else:
                    tag = msat_decl_get_tag(env, msat_term_get_decl(t))
                    func = tagmap.get(tag, unsupported)

                    idx = defn[0]
                    defn[0] += 1
                    ret = '__expr%d' % idx

                    if func is special:
                        if tag == MSAT_TAG_BV_EXTRACT:
                            ok, l, h = msat_term_is_bv_extract(e, t)
                            assert ok
                            func = lambda a: '%s[%d:%d]' % (a[0], l, h)
                        elif tag == MSAT_TAG_BV_SEXT:
                            ok, w = msat_term_is_bv_sext(e, t)
                            assert ok
                            ok, ww = msat_is_bv_type(e, msat_term_get_type(t))
                            assert ok
                            ww -= w
                            if ww:
                                func = lambda a: \
                                       '(case signed(%s) < signed(0ud%d_0) : ' \
                                       '0ud%d_1; TRUE: 0ud%d_0; esac) :: %s' % \
                                       (a[0], ww, w, w, a[0])
                            else:
                                func = lambda a: a[0]
                        elif tag == MSAT_TAG_BV_ZEXT:
                            ok, w = msat_term_is_bv_zext(e, t)
                            func = lambda a: '0ud%d_0 :: %s' % (w, a[0])
                            assert ok
                    
                    try:
                        defs.append('%s := %s;' % (ret, func(args)))
                    except Exception:
                        sys.stderr.write('UNSUPPORTED TAG: %s\n' % tag)
                        raise
                    cache[t] = ret
                
            return MSAT_VISIT_PROCESS
        
        msat_visit_term(env, term, visit)

    translate(model.init)
    translate(model.trans)
    for prop in model.invarprops:
        translate(prop)
    for prop in model.liveprops:
        translate(prop)

    pr('-- generated by %s on %s\n' %
       (os.path.basename(sys.argv[0]), time.ctime()))
    pr('MODULE main\n')
    if len(model.ivars):
        pr('IVAR\n')
        for name in sorted(model.ivars):
            declare_var(name)
        pr('\n')

    if len(model.svars):
        pr('VAR\n')
        for name in sorted(model.svars):
            declare_var(name)
        pr('\n')

    if defs:
        pr('DEFINE\n')
        for d in defs:
            pr(d)
            pr('\n')
        pr('\n')

    pr('INIT %s;\n' % cache[model.init])
    pr('TRANS %s;\n' % cache[model.trans])
    for prop in model.invarprops:
        pr('INVARSPEC %s;\n' % cache[prop])
    for prop in model.liveprops:
        pr('LTLSPEC F G (%s);\n' % cache[prop])
    


def main():
    parser = optparse.OptionParser('''\
%prog [SOURCE or stdin]

If SOURCE is a dir, it is expected to contain a benchmark in the format
(init.smt2, trans.smt2, property.smt2). If SOURCE is a file, it is expected
to be in "vmt2" format.

Output goes to stdout.\
''')
    
    opts, args = parser.parse_args()
    if len(args) > 1:
        parser.print_help()
        exit(0)
    elif len(args) == 1:
        src = args[0]
    else:
        src = sys.stdin
        
    env = msat_create_env()

    model = getmodel(env, src)
    try:
        to_nuxmv(env, model, sys.stdout)
    except Unsupported as e:
        sys.stderr.write("ERROR: unsupported operation: %s\n" % e.op)
    msat_destroy_env(env)


if __name__ == '__main__':
    main()
