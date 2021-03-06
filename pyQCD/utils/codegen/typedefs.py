"""This module contains the a series of classes for holding type information,
which is used to produce Cython syntax trees for the various types."""

from __future__ import absolute_import


class TypeDef(object):
    """Encapsulates type defintion and facilitates cython node generation."""

    def __init__(self, name, cname, cmodule, wrap_ptr, builtin=False):
        """Constructor for TypeDef object, See help(TypeDef)."""
        self.name = name
        self.cname = cname
        self.cmodule = cmodule
        self.wrap_ptr = wrap_ptr
        self.builtin = builtin

    def accessor(self, varname, broadcast=False):
        if self.builtin:
            return varname
        else:
            return "{}.instance{}{}".format(varname,
                                            "[0]" if self.wrap_ptr else "",
                                            ".broadcast()" if broadcast else "")


class ContainerDef(TypeDef):
    """Encapsulates container definition and facilitates cython node generation.
    """

    def __init__(self, name, cname, cmodule, size_expr, shape_expr, ndims_expr,
                 buffer_ndims, element_type, static_alloc_temp):
        """Constructor for ContainerDef object. See help(ContainerDef)"""
        super(ContainerDef, self).__init__(name, cname, cmodule, True)
        self.element_type = element_type
        self.size_expr = size_expr
        self.ndims_expr = ndims_expr
        self.structure = [self.__class__.__name__.replace("Def", "")]
        self.static_alloc_temp = static_alloc_temp
        if isinstance(element_type, ContainerDef):
            self.structure.extend(element_type.structure)
        try:
            self.buffer_ndims = element_type.buffer_ndims + buffer_ndims
        except AttributeError:
            self.buffer_ndims = buffer_ndims
        try:
            eval(shape_expr)
        except NameError:
            self._shape_expr = "self.instance[0].{}".format(shape_expr)
        else:
            self._shape_expr = shape_expr
        try:
            eval(ndims_expr)
        except NameError:
            self.ndims_expr = "self.instance[0].{}".format(ndims_expr)
        else:
            self.ndims_expr = ndims_expr
        try:
            int(size_expr)
        except ValueError:
            self.is_static = False
        else:
            self.is_static = True

    @property
    def matrix_shape(self):
        """The shape of the root child element type, if it exists"""
        if isinstance(self, MatrixDef):
            return self.shape
        else:
            return self.element_type.matrix_shape

    def unpack(self):
        """Returns a list of TypeDef instances"""
        out = [self]
        try:
            out.extend(self.element_type.unpack())
        except AttributeError:
            pass
        return out

    @property
    def shape_expr(self):
        """Generate expression for the shape of this container"""
        out = self.wrap_shape_expr(self._shape_expr)
        if isinstance(self.element_type, ContainerDef):
            sub_shape_expr = self.element_type.shape_expr
            sub_shape_expr = sub_shape_expr.replace("instance[0]",
                                                    "instance[0][0]")
            out = "{} + {}".format(out, sub_shape_expr)
        return out

    def wrap_shape_expr(self, expr):
        """Wraps the shape expression to put it in the right format"""
        return expr


class MatrixDef(ContainerDef):
    """Specialise container definition for matrix type"""

    def __init__(self, name, cname, cmodule, shape, element_type):
        """Constructor for MatrixDef object. See help(MatrixDef)"""
        size = reduce(lambda x, y: x * y, shape)
        super(MatrixDef, self).__init__(
            name, cname, cmodule, str(size), str(shape), str(len(shape)),
            len(shape), element_type,
            "{}.{}({}.{{}}())".format(cmodule, cname, cmodule))
        self.shape = shape
        self.is_matrix = len(self.shape) == 2
        self.is_square = self.is_matrix and self.shape[0] == self.shape[1]


class ArrayDef(ContainerDef):
    """Specialise container definition for array type"""

    def __init__(self, name, cname, cmodule, element_type):
        """Constructor for ArrayDef object. See help(ArrayDef)."""
        super(ArrayDef, self).__init__(
            name, cname, cmodule, "size()", "size()", "1", 1, element_type,
            "{}.{}(size, {{}})".format(cmodule, cname))

    def wrap_shape_expr(self, expr):
        """Put shape expression into a tuple"""
        return "({},)".format(expr)


class LatticeDef(ContainerDef):
    """Specialise container definition for lattice type"""

    def __init__(self, name, cname, cmodule, element_type):
        """Constructor for LatticeDef object. See help(LatticeDef)"""
        super(LatticeDef, self).__init__(
            name, cname, cmodule, "volume()", "lattice_shape()", "num_dims()",
            1, element_type,
            "{}.{}(layout.instance[0], {{}})".format(cmodule, cname))

    def wrap_shape_expr(self, expr):
        """Ensure shape expression is a tuple"""
        return "tuple({})".format(expr)
