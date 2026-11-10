{% macro generate_stable_key(columns) -%}
    md5(concat(
        {%- for column in columns %}
            {%- if not loop.first %}, '|', {% endif -%}
            coalesce(
                length(({{ column }})::text)::text || ':' || ({{ column }})::text,
                '-1:'
            )
        {%- endfor %}
    ))
{%- endmacro %}
