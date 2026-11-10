{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set target_schema = target.schema | lower -%}
    {%- set allowed_model_schemas = ['staging', 'intermediate', 'marts'] -%}

    {%- if target_schema != 'dbt_dev' -%}
        {{ exceptions.raise_compiler_error(
            "The ecommerce_dbt profile must target schema 'dbt_dev'; "
            ~ "refusing target schema '" ~ target.schema ~ "'."
        ) }}
    {%- endif -%}

    {%- if node.resource_type == 'test' -%}
        {{ target_schema }}_marts
    {%- elif node.resource_type != 'model' -%}
        {{ exceptions.raise_compiler_error(
            "Only dbt models and tests are permitted in this project; "
            ~ "refusing resource type '" ~ node.resource_type ~ "'."
        ) }}
    {%- elif custom_schema_name is none -%}
        {{ exceptions.raise_compiler_error(
            "Every dbt model must declare an allowed staging, intermediate, "
            ~ "or marts schema."
        ) }}
    {%- else -%}
        {%- set requested_schema = custom_schema_name | trim | lower -%}
        {%- if requested_schema not in allowed_model_schemas -%}
            {{ exceptions.raise_compiler_error(
                "Unsupported dbt model schema '" ~ custom_schema_name
                ~ "'; allowed schemas are dbt_dev_staging, "
                ~ "dbt_dev_intermediate, and dbt_dev_marts."
            ) }}
        {%- endif -%}
        {{ target_schema }}_{{ requested_schema }}
    {%- endif -%}
{%- endmacro %}
