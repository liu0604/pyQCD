"""This module contains functions for generating attribute and member function
code for each of the core types in core.pyx"""

from .typedefs import ArrayDef, LatticeDef, MatrixDef


def allocation_code(typedef):
    """Generate code for constructors and destructors.

    Args:
      typedef (ContainerDef): A ContainerDef instance specifying the type to
        generate code for.
    """
    from . import env
    template = env.get_template("core/allocation.pyx")

    args = []
    if "Lattice" in typedef.structure:
        args.append(("Layout", "layout", ".instance[0]"))
    if "Array" in typedef.structure:
        args.append(("int", "size", ""))

    rhs = "zeros"

    for i, tdef in enumerate(typedef.unpack()[::-1]):
        rhs = tdef.static_alloc_temp.format(rhs)

    argstring = ", ".join([" ".join(a[:2]) for a in args])
    argpass = ", ".join([n + a for t, n, a in args if n != "size"])

    return template.render(typedef=typedef,
                           argstring=argstring, argpass=argpass,
                           constructor_call=rhs)


def setget_code(typedef, precision):
    """Generate code for __setitem__ and __getitem__ member functions.

    Args:
      typedef (ContainerDef): A ContainerDef instance specifying the type to
        generate code for.
      precision (str): The fundamental machine type for representing real
        numbers.
    """
    from . import env
    template = env.get_template("core/setget.pyx")
    return template.render(typedef=typedef, precision=precision)


def buffer_code(typedef, precision):
    """Generate code for __getbuffer__ and __releasebuffer__ member functions.

    Args:
      typedef (ContainerDef): A ContainerDef instance specifying the type to
        generate code for.
      precision (str): The fundamental machine type for representing real
        numbers.
    """
    from . import env
    template = env.get_template("core/buffer.pyx")

    stride_length = "itemsize"
    inst_ref = typedef.accessor("self")
    buffer_info = []
    types = typedef.unpack()
    it = enumerate(types)

    for depth, tdef in reversed(list(it)):
        if type(tdef) is MatrixDef:
            buffer_info.append((stride_length, tdef.shape[0]))
            if len(tdef.shape) > 1:
                buffer_info.insert(0,
                                   (stride_length + " * " + str(tdef.shape[1]),
                                    tdef.shape[1]))
            stride_length += " * {}".format(tdef.size_expr)
        else:
            size_expr = inst_ref + "[0]" * depth + "." + tdef.size_expr
            buffer_info.append((stride_length, size_expr))
            stride_length += " * {}".format(size_expr)

    return template.render(typedef=typedef, precision=precision,
                           buffer_info=buffer_info[::-1],
                           buffer_size=stride_length)


def member_func_code(typedef):
    """Generate code for zeros, ones, identity and similar static initialisers.

    Args:
      typedef (ContainerDef): A ContainerDef instance specifying the type to
        generate code for.
    """
    from . import env
    template = env.get_template("core/member_funcs.pyx")
    try:
        is_square = typedef.matrix_shape[0] == typedef.matrix_shape[1]
    except IndexError:
        is_square = False
    funcnames = ["zeros", "ones"] + (["identity"] if is_square else [])

    args = []
    if "Lattice" in typedef.structure:
        args.append(("Layout", "layout"))
    if "Array" in typedef.structure:
        args.append(("int", "size"))

    rhs = ""

    for i, tdef in enumerate(typedef.unpack()[::-1]):
        cname = "{}.{}".format(tdef.cmodule, tdef.cname)
        if type(tdef) is MatrixDef:
            rhs = "{}.{{}}()".format(tdef.cmodule)
        if type(tdef) is ArrayDef:
            rhs = "{}(size, {})".format(cname, rhs)
        if type(tdef) is LatticeDef:
            rhs = "{}(layout.instance[0], {})".format(cname, rhs)
    static_assign_line = "out.instance[0] = {}".format(rhs)

    argstring = ", ".join([" ".join(a) for a in args])
    argpass = ", ".join([n for t, n in args if n != "size"])

    return template.render(typedef=typedef, funcnames=funcnames,
                           static_assign_line=static_assign_line,
                           argstring=argstring, argpass=argpass)
