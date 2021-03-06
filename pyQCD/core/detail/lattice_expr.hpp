#ifndef LATTICE_EXPR_HPP
#define LATTICE_EXPR_HPP

/* This file provides expression templates for the Lattice class, so that
 * temporaries do not need to be created when performing arithmetic operations.
 */

#include <memory>
#include <typeinfo>
#include <type_traits>

#include <utils/macros.hpp>
#include <utils/templates.hpp>

#include "../layout.hpp"
#include "lattice_traits.hpp"
#include "operators.hpp"


namespace pyQCD
{
  class LatticeObj { };

  // TODO: Eliminate need for second template parameter
  template <typename T1, typename T2>
  class LatticeExpr : public LatticeObj
  {
    // This is the main expression class from which all others are derived. It
    // uses CRTP to escape inheritance. Parameter T1 is the expression type
    // and T2 is the fundamental type contained in the Lattice. This allows
    // expressions to be abstracted to a nested hierarchy of types. When the
    // compiler goes through and does it's thing, the definitions of the
    // operations within these template classes are all spliced together.

  public:
    // CRTP magic - call functions in the Lattice class
    typename ExprReturnTraits<T1, T2>::type operator[](const int i)
    { return static_cast<T1&>(*this)[i]; }
    const typename ExprReturnTraits<T1, T2>::type operator[](const int i) const
    { return static_cast<const T1&>(*this)[i]; }

    unsigned long size() const { return static_cast<const T1&>(*this).size(); }
    const Layout* layout() const
    { return static_cast<const T1&>(*this).layout(); }

    operator T1&() { return static_cast<T1&>(*this); }
    operator T1 const&() const { return static_cast<const T1&>(*this); }
  };


  template <typename T>
  class LatticeConst
    : public LatticeExpr<LatticeConst<T>, T>
  {
    // Expression subclass for const operations
  public:
    // Need some SFINAE here to ensure no clash with copy/move constructor
    template <typename std::enable_if<
      not std::is_same<T, LatticeConst<T> >::value>::type* = nullptr>
    LatticeConst(const T& scalar) : scalar_(scalar) { }
    const T& operator[](const unsigned long i) const { return scalar_; }

  private:
    const T& scalar_;
  };


  template <typename T1, typename T2, typename Op>
  class LatticeUnary
    : public LatticeExpr<LatticeUnary<T1, T2, Op>,
        decltype(Op::apply(std::declval<T2>()))>
  {
  public:
    LatticeUnary(const LatticeExpr<T1, T2>& operand) : operand_(operand) { }

    const decltype(Op::apply(std::declval<T2>()))
    operator[](const unsigned int i) const { return Op::apply(operand_[i]); }

    unsigned long size() const { return operand_.size(); }
    const Layout* layout() const { return operand_.layout(); }

  private:
    typename OperandTraits<T1>::type operand_;
  };


  template <typename T1, typename T2, typename T3, typename T4, typename Op>
  class LatticeBinary
    : public LatticeExpr<LatticeBinary<T1, T2, T3, T4, Op>,
        decltype(Op::apply(std::declval<T3>(), std::declval<T4>()))>
  {
  // Expression subclass for binary operations
  public:
    LatticeBinary(const LatticeExpr<T1, T3>& lhs, const LatticeExpr<T2, T4>& rhs)
      : lhs_(lhs), rhs_(rhs)
    {
      pyQCDassert((BinaryOperandTraits<T1, T2>::equal_size(lhs_, rhs_)),
        std::out_of_range("LatticeBinary: lhs.size() != rhs.size()"));
      pyQCDassert((BinaryOperandTraits<T1, T2>::equal_layout(lhs_, rhs_)),
        std::bad_cast());
    }
    // Here we denote the actual arithmetic operation.
    const decltype(Op::apply(std::declval<T3>(), std::declval<T4>()))
    operator[](const unsigned long i) const
    { return Op::apply(lhs_[i], rhs_[i]); }

    unsigned long size() const
    { return BinaryOperandTraits<T1, T2>::size(lhs_, rhs_); }
    const Layout* layout() const
    { return BinaryOperandTraits<T1, T2>::layout(lhs_, rhs_); }

  private:
    // The members - the inputs to the binary operation
    typename OperandTraits<T1>::type lhs_;
    typename OperandTraits<T2>::type rhs_;
  };


  // This class allows for slicing of Lattice objects without copying data
  template <typename T1, typename T2>
  class LatticeView : public LatticeExpr<LatticeView<T1, T2>, T1>
  {
  public:
    template <template <typename> class Alloc>
    LatticeView(Lattice<T1, Alloc>& lattice,
                const std::vector<unsigned int>& slice, const unsigned int dim)
      : layout_(std::vector<unsigned int>{lattice.shape()[dim]})
    {
      std::vector<unsigned int> site = slice;
      site.insert(site.begin() + dim, 0);
      references_.resize(lattice.shape()[dim]);
      for (unsigned int i = 0; i < lattice.shape()[dim]; ++i) {
        site[dim] = i;
        references_[layout_.get_array_index(i)] = &lattice(site);
      }
    }

    unsigned long size() const { return references_.size(); }
    const Layout* layout() const { return &layout_; }

    T1& operator[](const unsigned int i) { return *(references_[i]); }
    const T1& operator[](const unsigned int i) const
    { return *(references_[i]); }

    T1& operator()(const unsigned int i)
    { return *(references_[layout_.get_array_index(i)]); }
    const T1& operator()(const unsigned int i) const
    { return *(references_[layout_.get_array_index(i)]); }
    template <typename U>
    T1& operator()(const U& site)
    { return *(references_[layout_.get_array_index(site)]); }
    template <typename U>
    const T1& operator()(const U& site) const
    { return *(references_[layout_.get_array_index(site)]); }

    T2 create_layout() const { return layout_; }
    template <template <typename> class Alloc>
    Lattice<T1, Alloc> create_lattice(const Layout& layout) const
    {
      auto out = Lattice<T1, Alloc>(layout);
      for (unsigned int i = 0; i < layout.volume(); ++i) {
        out(i) = (*this)(i);
      }
      return out;
    };

  private:
    T2 layout_;
    std::vector<T1*> references_;
  };

  // Some macros for the operator overloads, as the code is almost
  // the same in each case. For the scalar multiplies I've used
  // some SFINAE to disable these more generalized functions when
  // a LatticeExpr is used.
#define LATTICE_EXPR_OPERATOR(op, trait)                              \
  template <typename T1, typename T2, typename T3, typename T4>       \
  const LatticeBinary<T1, T2, T3, T4, trait>                          \
  operator op(const LatticeExpr<T1, T3>& lhs,                         \
    const LatticeExpr<T2, T4>& rhs)                                   \
  {                                                                   \
    return LatticeBinary<T1, T2, T3, T4, trait>(lhs, rhs);            \
  }                                                                   \
                                                                      \
                                                                      \
  template <typename T1, typename T2, typename T3,                    \
    typename std::enable_if<                                          \
      not std::is_base_of<LatticeObj, T3>::value>::type* = nullptr>   \
  const LatticeBinary<T1, LatticeConst<T3>, T2, T3, trait>            \
  operator op(const LatticeExpr<T1, T2>& lattice, const T3& scalar)   \
  {                                                                   \
    return LatticeBinary<T1, LatticeConst<T3>, T2, T3, trait>         \
      (lattice, LatticeConst<T3>(scalar));                            \
  }

  // This macro is for the + and * operators where the scalar can
  // be either side of the operator.
#define LATTICE_EXPR_OPERATOR_REVERSE_SCALAR(op, trait)               \
  template <typename T1, typename T2, typename T3,                    \
    typename std::enable_if<                                          \
      not std::is_base_of<LatticeObj, T1>::value>::type* = nullptr>   \
  const LatticeBinary<LatticeConst<T1>, T2, T1, T3, trait>            \
  operator op(const T1& scalar, const LatticeExpr<T2, T3>& lattice)   \
  {                                                                   \
    return LatticeBinary<LatticeConst<T1>, T2, T1, T3, trait>         \
      (LatticeConst<T1>(scalar), lattice);                            \
  }


  LATTICE_EXPR_OPERATOR(+, Plus);
  LATTICE_EXPR_OPERATOR_REVERSE_SCALAR(+, Plus);
  LATTICE_EXPR_OPERATOR(-, Minus);
  LATTICE_EXPR_OPERATOR(*, Multiplies);
  LATTICE_EXPR_OPERATOR_REVERSE_SCALAR(*, Multiplies);
  LATTICE_EXPR_OPERATOR(/, Divides);
}

#endif