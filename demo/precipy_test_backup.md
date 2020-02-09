<style>
    @page {
        size: letter landscape;
        margin: 2cm;
    }
</style>

## Welcome

Adding some text here too.

This is some text.

Here is a list of keys:
{% for k in keys %}
### {{ k }}

{% if data[k].files is defined %}
{% for cn, info in data[k].files.items() %}
- {{ cn  }}
{% for kk, vv in info.items() -%}
     - [{{ kk }}]({{ vv }}) : {{ vv }}
{% endfor -%}
{% if data[k].files[cn]['url'].endswith(".png") %}
![Plot]({{ data[k].files[cn]['url'] }})
{% endif %}
{% endfor %}
{% endif %}


{% endfor %}
