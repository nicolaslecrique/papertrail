"""Static-ish guards for the Jinja templates.

Complements djlint (HTML well-formedness) by loading every template through the
app's own Jinja environment: this compiles each one, catching Jinja syntax
errors, and proves each is discoverable by name. Together with StrictUndefined,
a missing variable or a missing partial fails a test instead of silently
rendering a blank.
"""

from jinja2 import StrictUndefined

from app.main import templates


def test_strict_undefined_is_configured() -> None:
    # A typo'd or missing template variable must raise, not render blank.
    assert templates.env.undefined is StrictUndefined


def test_all_templates_compile() -> None:
    names = templates.env.list_templates(extensions=["html"])
    assert names, "no templates were discovered under app/templates"
    for name in names:
        # get_template parses/compiles the source; malformed {% %} raises here.
        templates.env.get_template(name)
