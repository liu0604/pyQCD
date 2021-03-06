from {{ typedef.element_type.cmodule }} cimport {{ typedef.element_type.cname }}


cdef extern from "types.hpp":
    cdef cppclass {{ typedef.cname }}:
        {{ typedef.cname }}() except +
        {{ typedef.cname }}(const {{ typedef.cname }}&) except +
        {{ typedef.cname }} adjoint()
        {% if typedef.shape|length > 1 %}
        {{ typedef.element_type.cname }}& operator()(int, int) except +
        {% else %}
        {{ typedef.element_type.cname }}& operator[](int) except +
        {% endif %}


    cdef {{ typedef.cname }} zeros "{{ typedef.cname }}::Zero"()
    cdef {{ typedef.cname }} ones "{{ typedef.cname }}::Ones"()
{% if typedef.is_square %}
    cdef {{ typedef.cname }} identity "{{ typedef.cname }}::Identity"()
{% endif %}
    cdef void mat_assign({{ typedef.cname }}&, const int, const int, const Complex)
    cdef void mat_assign({{ typedef.cname }}*, const int, const int, const Complex)