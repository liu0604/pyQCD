"""This module contains template tags for generating arithmetic operations
for the specified Cython types."""

from .typedefs import ArrayDef, LatticeDef, TypeDef


def scalar_typedefs(precision):
    """Generate scalar type definitions for use in operator overloading"""
    return [TypeDef("int", "int", "", False, True),
            TypeDef("float", precision, "", False, True),
            TypeDef("Complex", "Complex", "complex", False)]


def filter_types(typedef, matrix_shape, is_array, is_lattice):
    """Determine whether supplied typedef fits the specified requirements"""
    correct_shape = typedef.matrix_shape == matrix_shape
    is_array_correct = (isinstance(typedef, ArrayDef) == is_array or
                        isinstance(typedef.element_type, ArrayDef))
    is_lattice_correct = isinstance(typedef, LatticeDef) == is_lattice
    return correct_shape and is_array_correct and is_lattice_correct


def generate_scalar_operations(operations, typedef, scalar_typedefs):
    """Add scalar operations to the operations dictionary.

    Args:
      operations (dict): A dictionary containing lists of tuples specifying
        the arithmetic operations.
      typedef (ContainerDef): A ContainerDef instance specifying the type to
        generate operations for.
      scalar_typedefs (iterable): An iterable of TypeDef instances specifying
        the scalar types to add operations for.
    """
    for scalar_typedef in scalar_typedefs:
        operations["*"].append((typedef, scalar_typedef, typedef, None))
        for op in "*/":
            operations[op].append((typedef, typedef, scalar_typedef, None))

    return operations


def generate_matrix_operations(operations, lhs, rhss):
    """Generate a list of tuples specifying operations and operand types.

    Args:
      operations (dict): A dictionary containing lists of tuples specifying
        the arithmetic operations.
      typedef (ContainerDef): A ContainerDef instance specifying the type to
        generate operations for.
      other_typedefs (iterable): An iterable of ContainerDef instances to
        compare the supplied typedef variable against.
    """
    lhs_is_lattice = isinstance(lhs, LatticeDef)
    lhs_is_array = (isinstance(lhs, ArrayDef) or
                    isinstance(lhs.element_type, ArrayDef))

    for rhs in rhss:
        rhs_is_lattice = isinstance(rhs, LatticeDef)
        rhs_is_array = (isinstance(rhs, ArrayDef) or
                        isinstance(rhs.element_type, ArrayDef))
        if rhs_is_lattice != lhs_is_lattice:
            continue
        result_is_lattice = lhs_is_lattice or rhs_is_lattice
        result_is_array = lhs_is_array or rhs_is_array
        try:
            result_shape = lhs.matrix_shape[0], rhs.matrix_shape[1]
        except IndexError:
            result_shape = lhs.matrix_shape[0],
        filter_args = result_shape, result_is_array, result_is_lattice
        try:
            result_typedef = [e for e in rhss
                              if filter_types(e, *filter_args)][0]
        except IndexError:
            continue
        try:
            can_multiply = lhs.matrix_shape[1] == rhs.matrix_shape[0]
        except IndexError:
            can_multiply = False
        can_addsub = (lhs.matrix_shape == rhs.matrix_shape and
                      lhs_is_array == rhs_is_array)

        if can_multiply:
            operations["*"].append((result_typedef, lhs, rhs, None))
        if can_addsub:
            for op in "+-":
                operations[op].append((result_typedef, lhs, rhs, None))

    return operations


def arithmetic_code(typedef, typedefs):
    """Generate code for constructors and destructors.

    Args:
      typedef (ContainerDef): A ContainerDef instance specifying the type to
        generate code for.
      typedefs (iterable): An iterable of ContainerDef instances to compare
        the specified typedef to.
      precision (str): String specifying the fundamental real numerical type.
    """
    operator_map = {"*": ["mul"], "/": ["div", "truediv"],
                    "+": ["add"], "-": ["sub"]}
    operations = {'*': [], '/': [], '+': [], '-': []}
    complex_types = {'*': True, '/': True, '+': False, '-': False}
    generate_matrix_operations(operations, typedef, typedefs)

    from . import env
    template = env.get_template("core/arithmetic.pyx")
    return template.render(typedef=typedef, operations=operations,
                           operator_map=operator_map,
                           lhs_complex=complex_types, rhs_complex=complex_types)
