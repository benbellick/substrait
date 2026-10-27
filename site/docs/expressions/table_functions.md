# Table Functions

Table functions produce zero or more rows per invocation. Unlike scalar functions, which produce a single value, a table function call has a struct output type whose fields represent the generated columns.

A table function call is represented by the `TableFunction` message. The [Table Function relation](../relations/logical_relations.md#table-function) contains the call in its `function` field and returns its generated rows.

## Function Definition Properties

Table functions are declared under `table_functions` in extension YAML files.

| Property | Description | Required |
| -------- | ----------- | -------- |
| Name | A case-sensitive UTF-8 name used to reference the function. | Required |
| List of arguments | Value, type, or enumeration arguments, following [scalar function argument types](scalar_functions.md#argument-types). | Optional, defaults to niladic. |
| Variadic Behavior | Whether the last argument can be repeated, with optional minimum and maximum counts. | Optional, defaults to a single argument. |
| Options | Named behavioral options declared per implementation, following the [scalar function option mechanism](scalar_functions.md#options). | Optional |
| Description | Human-readable description of the function or an individual implementation. | Optional |
| Return Type | A type expression that resolves to a non-nullable struct. May be omitted when the producer determines the schema from argument values or external information. | Optional, see [Schema Determination](#schema-determination). |
| Implementation Map | Locations of function implementations. | Optional |

Options follow the [scalar function option rules](scalar_functions.md#options).

## Table Function Calls

| Field | Description | Required |
| ----- | ----------- | -------- |
| `function_reference` | A function anchor in the plan referring to a table function in an extension YAML file. Zero is valid, though non-zero anchors are preferred for ergonomics. | Required |
| `arguments` | Arguments matching the selected implementation's signature, including any variadic arguments. | Optional for niladic functions. |
| `options` | Named behavioral preferences using the implementation's declared options. | Optional |
| `output_type` | The concrete `Type.Struct` schema of every generated row, with `nullability` set to `NULLABILITY_REQUIRED`. | Required |

Value arguments use `FunctionArgument.value`, type arguments use `FunctionArgument.type`, and enumeration arguments use `FunctionArgument.enum`. Arguments are not restricted to literals unless the function definition requires a constant argument.

Table functions always follow the [scalar `DECLARED_OUTPUT` nullability rules](scalar_functions.md#nullability-handling), with the additional requirement that the output type is a non-nullable struct.

## Schema Determination

Every call must declare a concrete `output_type`, regardless of whether its YAML implementation declares a `return` expression. The output type is fixed for the call, and every generated row must conform to it.

### Schemas Derivable from YAML

If an implementation declares `return`, the call's `output_type` must match that expression evaluated with the bound argument types.

### Schemas Determined by Plan Producer

An implementation may omit `return` when the producer determines the output schema using argument values, external information, or other function-specific knowledge rather than a YAML type expression. No additional marker is required. The producer must still provide the concrete schema in the call's `output_type` field.

For example, this parsing function uses a schema-defining string argument to determine its output columns. Its YAML definition intentionally omits `return`.

```yaml
--8<-- "examples/extensions/producer_resolved_table_function.yaml"
```

The producer resolves the schema argument's value and declares the resulting struct in the function call. Function anchor 1 refers to `parse_records:str_str` from the example extension.

```protobuf
--8<-- "examples/proto-textformat/table_function/producer_resolved_schema.textproto"
```

## Multi-List Unnest

`unnest` has fixed-arity overloads for one through four lists. Each argument has an independent type parameter, so lists may have different element types. Each list contributes one output column in argument order.

| Argument types | Return type |
| -------------- | ----------- |
| `list<any1>` | `struct<any1>` |
| `list<any1>`, `list<any2>` | `struct<any1?, any2?>` |
| `list<any1>`, `list<any2>`, `list<any3>` | `struct<any1?, any2?, any3?>` |
| `list<any1>`, `list<any2>`, `list<any3>`, `list<any4>` | `struct<any1?, any2?, any3?, any4?>` |

Multiple lists are expanded in parallel, not as a cross product. Shorter lists are padded with NULLs, so all output fields of multi-list overloads are nullable. The single-list overload preserves the element type's nullability.

These overloads enumerate the currently supported signatures, not a fundamental limit of table functions. General type derivation for an arbitrary number of output columns is left for future work.

## Standalone Invocation Examples

These examples are `TableFunctionRel` messages. Each contains the function call in its `function` field. Function anchor 1 refers to the indicated function in the `functions_table` extension.

### Generating a Sequence

All `generate_series` overloads require an explicit `step` argument. Producers must supply any default chosen by the source query language.

If any argument is NULL, the result is empty. Otherwise, a zero `step` raises an error.

Generate integers from 1 to 100 using `generate_series:i64_i64_i64` with an explicit step of 1.

```protobuf
--8<-- "examples/proto-textformat/table_function_rel/generate_series.textproto"
```

The SQL equivalent is `SELECT * FROM generate_series(1, 100, 1)`.

### Unnesting a Single List

Unnest a string list using `unnest:list`.

```protobuf
--8<-- "examples/proto-textformat/table_function_rel/unnest_single_list.textproto"
```

The output contains three rows with values `apple`, `banana`, and `cherry`.

### Unnesting Multiple Lists

Unnest an integer list and a shorter string list using `unnest:list_list`, padding the shorter list with NULL.

```protobuf
--8<-- "examples/proto-textformat/table_function_rel/unnest_multiple_lists.textproto"
```

The PostgreSQL equivalent is `SELECT * FROM UNNEST(ARRAY[1, 2], ARRAY['a'])`.

```text
element1 | element2
---------+---------
1        | a
2        | NULL
```

=== "TableFunction Message"

    ```proto
%%% proto.algebra.TableFunction %%%
    ```
