#!/usr/bin/env python

"""
A converter from BTOR to nuXmv or SMT format
"""


import os, sys
import optparse
from mathsat import *
import vmt2nuxmv
import time


bvcontext = 0
boolcontext = 1

# a type is either an int (the width of the bv) or a tuple (for arrays)
booltype = 1

def is_bv(tp): return isinstance(tp, int)
def is_array(tp): return isinstance(tp, tuple) and len(tp) == 2


class BTORConverter(object):
    def __init__(self, env):
        self.symtbl_ = {}
        self.novar_ = object()
        self.env = env
        self.roots = []
        self.registers = []
        self.memorys = []

    def get(self, idx, context):
        t = self.symtbl_[abs(idx)][context]
        if idx < 0:
            if context == boolcontext:
                t = msat_make_not(self.env, t)
            else:
                t = msat_make_bv_not(self.env, t)
        return t

    def set(self, idx, term, tp):
        assert idx not in self.symtbl_
        if tp == booltype:
            tt = msat_make_term_ite(self.env, term,
                                    msat_make_bv_number(self.env, "1", 1, 10),
                                    msat_make_bv_number(self.env, "0", 1, 10))
            if not MSAT_ERROR_TERM(tt):
                t2 = term
                term = tt
            else:
                t2 = msat_make_equal(self.env, term,
                                     msat_make_bv_number(self.env, "1", 1, 10))
        else:
            t2 = self.novar_
        self.symtbl_[idx] = (term, t2)

    def mk_var(self, idx, name, tp):
        assert idx not in self.symtbl_
        if not name: name = "v%d" % idx
        d = msat_declare_function(self.env, name, self.get_type_(tp))
        v = msat_make_constant(self.env, d)
        if tp == booltype:
            vv = v
            v = msat_make_term_ite(self.env, v,
                                   msat_make_bv_number(self.env, "1", 1, 10),
                                   msat_make_bv_number(self.env, "0", 1, 10))
        else:
            vv = self.novar_
        self.symtbl_[idx] = (v, vv)

    def mk_array_var(self, idx, etp, itp):
        assert idx not in self.symtbl_
        name = "a%d" % idx
        d = msat_declare_function(self.env, name, self.get_type_((itp, etp)))
        v = msat_make_constant(self.env, d)
        self.symtbl_[idx] = (v, self.novar_)        

    def get_type_(self, tp):
        if tp == booltype:
            return msat_get_bool_type(self.env)
        elif is_bv(tp):
            return msat_get_bv_type(self.env, tp)
        else:
            assert is_array(tp)
            itp = msat_get_bv_type(self.env, tp[0])
            etp = msat_get_bv_type(self.env, tp[1])
            return msat_get_array_type(self.env, itp, etp)

    def addroot(self, idx):
        r = self.get(idx, boolcontext)
        self.roots.append(r)

    def add_register(self, idx, w, v, e):
        self.registers.append((idx, w, v, e))
        self.set(idx, e, w)

    def add_memory(self, idx, ew, iw, a1, a2):
        self.memorys.append((idx, ew, iw, a1, a2))
        
# end of class BTORConverter


def make_xor(env, t1, t2):
    return msat_make_not(env, msat_make_iff(env, t1, t2))


def parse_bool_connective(boolop, bvop):
    if bvop is None:
        def func(btor, idx, w, a1, a2):
            assert w == 1
            btor.set(idx, boolop(btor.env, btor.get(a1, boolcontext),
                                 btor.get(a2, boolcontext)), w)
    else:
        def func(btor, idx, w, a1, a2):
            if w == 1:
                t1 = btor.get(a1, boolcontext)
                t2 = btor.get(a2, boolcontext)
                term = boolop(btor.env, t1, t2)
            else:
                term = bvop(btor.env, btor.get(a1, bvcontext),
                            btor.get(a2, bvcontext))
            btor.set(idx, term, w)
    return func


def parse_not(btor, idx, w, a):
    if w == 1:
        term = msat_make_not(btor.env, btor.get(a, boolcontext))
    else:
        term = msat_make_bv_not(btor.env, btor.get(a, bvcontext))
    btor.set(idx, term, w)


def parse_cond(btor, idx, w, a1, a2, a3):
    c = btor.get(a1, boolcontext)
    if w == 1:
        t = btor.get(a2, boolcontext)
        e = btor.get(a3, boolcontext)
        term = msat_make_and(btor.env,
                             msat_make_or(btor.env,
                                          msat_make_not(btor.env, c), t),
                             msat_make_or(btor.env, c, e))
    else:
        t = btor.get(a2, bvcontext)
        e = btor.get(a3, bvcontext)
        term = msat_make_term_ite(btor.env, c, t, e)
    btor.set(idx, term, w)


def parse_bv_neg(btor, idx, w, a):
    term = msat_make_bv_neg(btor.env, btor.get(a, bvcontext))
    btor.set(idx, term, w)
    

def parse_bv_op(bvop):
    def func(btor, idx, w, a1, a2):
        term = bvop(btor.env, btor.get(a1, bvcontext), btor.get(a2, bvcontext))
        assert not MSAT_ERROR_TERM(term)
        btor.set(idx, term, w)
    return func


def parse_equal(btor, idx, w, a1, a2):
    t1 = btor.get(a1, bvcontext)
    t2 = btor.get(a2, bvcontext)

    ok, idxt, elemt = msat_is_array_type(btor.env, msat_term_get_type(t1))
    if ok:
        term = msat_make_equal(btor.env, t1, t2)
    else:
        ok, tw = msat_is_bv_type(btor.env, msat_term_get_type(t1))
        assert ok
        ok, idxt, elemt = msat_is_array_type(btor.env, msat_term_get_type(t1))
        if tw == 1:
            term = msat_make_iff(btor.env, btor.get(a1, boolcontext),
                                 btor.get(a2, boolcontext))
        else:
            term = msat_make_equal(btor.env, t1, t2)
    btor.set(idx, term, w)


def parse_not_equal(btor, idx, w, a1, a2):
    t1 = btor.get(a1, bvcontext)
    t2 = btor.get(a2, bvcontext)

    ok, idxt, elemt = msat_is_array_type(btor.env, msat_term_get_type(t1))
    if ok:
        term = msat_make_equal(btor.env, t1, t2)
    else:
        ok, tw = msat_is_bv_type(btor.env, msat_term_get_type(t1))
        assert ok
        if tw == 1:
            term = msat_make_iff(btor.env, btor.get(a1, boolcontext),
                                 btor.get(a2, boolcontext))
        else:
            term = msat_make_equal(btor.env, t1, t2)
    term1 = msat_make_not(btor.env, term)
    btor.set(idx, term1, w)


def parse_bv_shift(bvop):
    def func(btor, idx, w, a1, a2):
        t1 = btor.get(a1, bvcontext)
        t2 = btor.get(a2, bvcontext)
        ok, w2 = msat_is_bv_type(btor.env, msat_term_get_type(t2))
        assert ok
        if w2 < w:
            t2 = msat_make_bv_zext(btor.env, w - w2, t2)
        term = bvop(btor.env, t1, t2)
        assert not MSAT_ERROR_TERM(term)
        btor.set(idx, term, w)
    return func



def parse_bv_slice(btor, idx, w, a, u, l):
    arg = btor.get(a, bvcontext)
    term = msat_make_bv_extract(btor.env, u, l, arg)
    btor.set(idx, term, w)


def parse_bv_var(btor, idx, w, name=""):
    btor.mk_var(idx, name, w)


def parse_bv_number(base):
    def func(btor, idx, w, value):
        val = int(str(value), base)
        if w == 1:
            if val: term = msat_make_true(btor.env)
            else: term = msat_make_false(btor.env)
        else:
            term = msat_make_bv_number(btor.env, str(val), w, 10)
        btor.set(idx, term, w)
    return func


def parse_zero(btor, idx, w):
    if w == 1:
        term = msat_make_false(btor.env)
    else:
        term = msat_make_bv_number(btor.env, "0", w, 10)
    btor.set(idx, term, w)


def parse_one(btor, idx, w):
    if w == 1:
        term = msat_make_true(btor.env)
    else:
        term = msat_make_bv_number(btor.env, "1", w, 10)
    btor.set(idx, term, w)


def parse_array(btor, idx, ew, iw):
    btor.mk_array_var(idx, ew, iw)

    
def parse_array_read(btor, idx, w, a1, a2):
    t1 = btor.get(a1, bvcontext)
    t2 = btor.get(a2, bvcontext)
    term = msat_make_array_read(btor.env, t1, t2)
    btor.set(idx, term, w)


def parse_array_write(btor, idx, ew, iw, a1, a2, a3):
    term = msat_make_array_write(btor.env, btor.get(a1, bvcontext),
                                 btor.get(a2, bvcontext),
                                 btor.get(a3, bvcontext))
    btor.set(idx, term, (iw, ew))


def parse_acond(btor, idx, etp, itp, a1, a2, a3):
    term = msat_make_term_ite(btor.env, btor.get(a1, boolcontext),
                              btor.get(a2, bvcontext),
                              btor.get(a3, bvcontext))
    btor.set(idx, term, (itp, etp))


def parse_array_next(btor, idx, ew, iw, a1, a2):
    btor.add_memory(idx, ew, iw, btor.get(a1, bvcontext), btor.get(a2, bvcontext))


def parse_root(btor, idx, w, arg):
    assert w == 1
    btor.addroot(arg)


def parse_next(btor, idx, w, v, e):
    if w == 1:
        ctx = boolcontext
    else:
        ctx = bvcontext
    btor.add_register(idx, w, btor.get(v, ctx), btor.get(e, ctx))


def parse_bv_ugt(btor, idx, w, a1, a2):
    t1 = btor.get(a1, bvcontext)
    t2 = btor.get(a2, bvcontext)
    t3 = msat_make_bv_uleq(btor.env, t1, t2)
    t4 = msat_make_not(btor.env, t3)
    btor.set(idx, t4, w)


def parse_bv_ugeq(btor, idx, w, a1, a2):
    t1 = btor.get(a1, bvcontext)
    t2 = btor.get(a2, bvcontext)
    t3 = msat_make_bv_ult(btor.env, t1, t2)
    t4 = msat_make_not(btor.env, t3)
    btor.set(idx, t4, w)


def parse_reduce_or(btor, idx, w, a):
    assert w == 1
    t1 = btor.get(a, bvcontext)
    ok, w1 = msat_is_bv_type(btor.env, msat_term_get_type(t1))
    assert ok
    t2 = msat_make_bv_number(btor.env, "1", w1, 10)
    t3 = msat_make_bv_ult(btor.env, t1, t2)
    t4 = msat_make_not(btor.env, t3)
    btor.set(idx, t4, w)


def parse_reduce_and(btor, idx, w, a):
    assert w == 1
    t1 = btor.get(a, bvcontext)
    ok, w1 = msat_is_bv_type(btor.env, msat_term_get_type(t1))
    assert ok
    t2 = msat_make_bv_number(btor.env, "0", w1, 10)
    t3 = msat_make_bv_not(btor.env, t1)
    t4 = msat_make_equal(btor.env, t3, t2)
    btor.set(idx, t4, w)


opmap = {
    "var" : parse_bv_var,
    "constd" : parse_bv_number(10),
    "consth" : parse_bv_number(16),
    "const" : parse_bv_number(2),
    "not" : parse_not,
    "and" : parse_bool_connective(msat_make_and, msat_make_bv_and),
    "or" : parse_bool_connective(msat_make_or, msat_make_bv_or),
    "xor" : parse_bool_connective(make_xor, msat_make_bv_xor),
    "neg" : parse_bv_neg,
    "cond" : parse_cond,
    "slice" : parse_bv_slice,
    "add" : parse_bv_op(msat_make_bv_plus),
    "mul" : parse_bv_op(msat_make_bv_times),
    "urem" : parse_bv_op(msat_make_bv_urem),
    "srem" : parse_bv_op(msat_make_bv_srem),
    "udiv" : parse_bv_op(msat_make_bv_udiv),
    "sdiv" : parse_bv_op(msat_make_bv_sdiv),
    "sub" : parse_bv_op(msat_make_bv_minus),
    "eq" : parse_equal,
    "ne" : parse_not_equal,
    "ult" : parse_bv_op(msat_make_bv_ult),
    "ulte" : parse_bv_op(msat_make_bv_uleq),
    "ugt" : parse_bv_ugt,
    "ugte" : parse_bv_ugeq,
    "concat" : parse_bv_op(msat_make_bv_concat),
    "array" : parse_array,
    "read" : parse_array_read,
    "write" : parse_array_write,
    "acond" : parse_acond,
    "anext" : parse_array_next,
    "root" : parse_root,
    "sll" : parse_bv_shift(msat_make_bv_lshl),
    "srl" : parse_bv_shift(msat_make_bv_lshr),
    "sra" : parse_bv_shift(msat_make_bv_ashr),
    "slt" : parse_bv_op(msat_make_bv_slt),
    "next" : parse_next,
    "zero" : parse_zero,
    "one" : parse_one,
    "redor" : parse_reduce_or,
    "redand" : parse_reduce_and,
    }


def toint(a):
    try: return int(a)
    except ValueError: return a


def warn(msg):
    sys.stderr.write('WARNING: %s\n' % msg)
    sys.stderr.flush()


def err(msg):
    sys.stderr.write('ERROR: %s\n' % msg)
    sys.stderr.flush()
    exit(1)


def main():
    p = optparse.OptionParser()
    p.add_option('-o', '--output')
    p.add_option('--vmt', action='store_false', dest='nuxmv',
                 help='dump in vmt format')
    p.add_option('--nuxmv', action='store_true',
                 help='dump in nuxmv format (default)')
    opts, _ = p.parse_args()
    if opts.nuxmv is None:
        opts.nuxmv = True
    
    env = msat_create_env()
    btor = BTORConverter(env)
    for line in sys.stdin:
        try:
            line = line[:line.index(';')]
        except ValueError:
            pass
        line = line.strip()
        if not line:
            continue
        tokens = line.split()
        if len(tokens) < 2:
            print line
            raise Exception(line)
        op = tokens[1]
        func = opmap[op]
        ## print ';; parsed %d %s' % (int(tokens[0]), op)
        ## sys.stdout.flush()
        args = [btor, int(tokens[0])] + [toint(t) for t in tokens[2:]]
        func(*args)

    formula = None
    init, trans, prop = None, None, None
    statevars = []
    
    if not btor.registers and not btor.memorys:
        term = msat_make_true(env)
        for r in btor.roots:
            term = msat_make_and(env, term, r)
        formula = term
    else:
        init = msat_make_true(env)
        for _, w, v, _ in btor.registers:
            if w == booltype:
                e = msat_make_not(env, v)
            else:
                val = msat_make_bv_number(env, "0", w, 10)
                e = msat_make_equal(env, v, val)
            init = msat_make_and(env, init, e)

        trans = msat_make_true(env)
        for _, w, v, e in btor.registers:
            d = msat_term_get_decl(v)
            n = msat_decl_get_name(d)
            nn = n + ".next"
            assert MSAT_ERROR_DECL(msat_find_decl(env, nn))
            dd = msat_declare_function(env, nn, msat_term_get_type(v))
            vn = msat_make_constant(env, dd)
            if w == booltype:
                c = msat_make_iff(env, vn, e)
            else:
                c = msat_make_equal(env, vn, e)
            trans = msat_make_and(env, trans, c)
            statevars.append((v, nn))
        for _, _, _, a1, a2 in btor.memorys:
            nn = "%s.next" % a1
            assert MSAT_ERROR_DECL(msat_find_decl(env, nn))
            dd = msat_declare_function(env, nn, msat_term_get_type(a1))
            vn = msat_make_constant(env, dd)
            c = msat_make_equal(env, vn, a2)
            trans = msat_make_and(env, trans, c)

        bad = msat_make_false(env)
        for r in btor.roots:
            bad = msat_make_or(env, bad, r)
        prop = msat_make_not(env, bad)

    if opts.nuxmv:
        if not btor.registers and not btor.memorys:
            warn('no registers/memories found, but nuXmv format requested')
            init = formula
            trans = msat_make_true(env)
            prop = msat_make_true(env)

        model = vmt2nuxmv.getmodel_formulas(env, init, trans, prop)
        if opts.output:
            with open(opts.output, 'w') as out:
                vmt2nuxmv.to_nuxmv(env, model, out)
        else:
            vmt2nuxmv.to_nuxmv(env, model, sys.stdout)
    else:
        sys.stdout.write(';; generated by %s on %s\n' %
                         (os.path.basename(sys.argv[0]), time.ctime()))
        if not btor.registers:
            smt2 = msat_to_smtlib2(env, formula)
            if opts.output:
                with open(opts.output, 'w') as f:
                    f.write(smt2)
            else:
                sys.stdout.write(smt2)
        else:
            terms = [init, trans, prop] + [c for (c, _) in statevars]
            annots = ["init", "true", "trans", "true", "invar-property", "0"] +\
                     sum((["next", "|%s|" % n] for (_, n) in statevars), [])
            smt2 = msat_annotated_list_to_smtlib2(env, terms, annots)
            if opts.output:
                with open(opts.output, 'w') as f:
                    f.write(smt2)
            else:
                sys.stdout.write(smt2)

    msat_destroy_env(env)


if __name__ == '__main__':
    main()

        
