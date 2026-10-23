# Table Functions

Table functions produce zero or more rows per invocation. Unlike scalar functions, which produce a single value, a table function call has a struct output type whose fields represent the generated columns.

The callable representation is the shared `TableFunction` message. Relational operators contain it directly and determine when the function is invoked and how its rows contribute to their output. The standalone [Table Function relation](../relations/logical_relations.md#table-function) evaluates it once in the current evaluation context. A separate per-input-row relation, such as the proposed [GenerateRel](https://github.com/substrait-io/substrait/pull/917), can use the same callable representation without defining another kind of table function.

## Function Definition Properties

Table functions are declared under `table_functions` in extension YAML files.

| Property | Description | Required |
| -------- | ----------- | -------- |
| Name | A case-sensitive UTF-8 name used to reference the function. | Required |
| List of arguments | Value, type, or enumeration arguments, following [scalar function argument types](scalar_functions.md#argument-types). | Optional, defaults to niladic. |
| Variadic Behavior | Whether the last argument can be repeated, with optional minimum and maximum counts. | Optional, defaults to a single argument. |
| Nullability Handling | Follows the [scalar function nullability modes](scalar_functions.md#nullability-handling). The return type must resolve to a non-nullable struct. | Optional, defaults to `MIRROR`. |
| Options | Named behavioral options declared per implementation, following the [scalar function option mechanism](scalar_functions.md#options). | Optional |
| Description | Human-readable description of the function. | Optional |
| Return Type | A type expression that resolves to a non-nullable struct. May be omitted when the producer determines the schema from argument values or external information. | Optional, see [Schema Determination](#schema-determination). |
| Implementation Map | Locations of function implementations. | Optional |

Each implementation may declare an `options` map in YAML. Each named option declares its allowed `values` and may include a `description`. Calls select preferences using `FunctionOption` in the protobuf `options` field. Options follow the same preference and omission rules as [scalar function options](scalar_functions.md#options) and are not part of the function signature.

## Table Function Calls

| Field | Description | Required |
| ----- | ----------- | -------- |
| `function_reference` | A function anchor in the plan referring to a table function in an extension YAML file. Zero is valid, though non-zero anchors are preferred for ergonomics. | Required |
| `arguments` | Arguments matching the selected implementation's signature, including any variadic arguments. | Optional for niladic functions. |
| `options` | Named behavioral preferences using the implementation's declared options. | Optional |
| `output_type` | The concrete, non-nullable struct type of every generated row. | Required |

Value arguments use `FunctionArgument.value`, type arguments use `FunctionArgument.type`, and enumeration arguments use `FunctionArgument.enum`. The containing relational operator determines the scope of field references. Arguments are not restricted to literals unless the function definition requires a constant argument.

A table function call is separate from `Expression` because it produces rows rather than a single value. Its output struct fields become generated columns in positional order; the struct is not emitted as a single column. Individual fields may be nullable, but a nullable outer struct does not represent an empty result. An empty result means zero rows.

Names are not part of the output type. A relation can supply optional names through `RelCommon.hint.output_names`, or a plan root can supply them through `RelRoot.names`.

## Schema Determination

Every call must declare a concrete `output_type`, regardless of whether its YAML implementation declares a `return` expression. The output type is fixed for the call, and every generated row must conform to it.

### Schemas Derivable from YAML

When an implementation declares `return`, the call's `output_type` must match that expression evaluated with the bound argument types and nullability rules.

Return expressions may be concrete or use type parameters bound from the arguments. The [functions_table extension](../extensions/functions_table.md) defines `generate_series` overloads with concrete return types of `struct<i64>` or `struct<i32>`.

### Schemas Determined by Plan Producer

An implementation may omit `return` when the producer determines the output schema using argument values, external information, or other function-specific knowledge rather than a YAML type expression. No additional marker is required. The producer must still provide the concrete schema in the call's `output_type` field.

For example, this parsing function uses a schema-defining string argument to determine its output columns. Its YAML definition intentionally omits `return`.

```yaml
--8<-- "examples/extensions/producer_resolved_table_function.yaml"
```

The producer resolves the schema argument's value and declares the resulting struct in the shared function call. Function anchor 1 refers to `parse_records:str_str` from the example extension.

```protobuf
--8<-- "examples/proto-textformat/table_function/producer_resolved_schema.textproto"
```

A function like `read_parquet(path)` may instead require inspecting a file's structure. The same contract applies. The columns cannot change between generated rows, including when a relational operator evaluates the call for successive input rows.

## Standalone Invocation Examples

These examples are `TableFunctionRel` messages. Each contains the shared call in its `function` field. Function anchor 1 refers to the indicated function in the `functions_table` extension.

### Generating a Sequence

All `generate_series` overloads require an explicit `step` argument. Producers must supply any default chosen by the source query language.

The `on_zero_step` option controls behavior when `step` is zero. `ERROR` raises an error, while `EMPTY` produces zero rows. If the option is omitted, the consumer chooses the behavior; the YAML value order does not define a default. A producer requiring an error must request only `ERROR`, and a consumer unable to provide that behavior must reject the plan.

Generate integers from 1 to 100 using `generate_series:i64_i64_i64` with an explicit step of 1. The example also requests `ERROR` for zero-step handling.

```protobuf
--8<-- "examples/proto-textformat/table_function_rel/generate_series.textproto"
```

The SQL equivalent is `SELECT * FROM generate_series(1, 100, 1)`.

The leaf relation can be composed with other relational operators. For example, placing a `FilterRel` above a `TableFunctionRel` filters the generated rows without changing the function call.

## Correlated Invocation

A standalone `TableFunctionRel` has no local input row, but its arguments may reference an enclosing scope when it appears within a correlated subquery. An inner [lateral join](../relations/logical_relations.md#lateral-join-operation) can evaluate the leaf relation once per left row using outer references to that row.

A dedicated per-input-row relation can instead invoke the same `TableFunction` directly against its input row and append the generated fields to the input fields. Such an operator controls row preservation when the function returns no rows; that behavior is separate from the function's own result.

=== "TableFunction Message"

    ```proto
%%% proto.algebra.TableFunction %%%
    ```
