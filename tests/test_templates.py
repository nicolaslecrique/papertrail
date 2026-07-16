"""Static-ish guards for the Jinja templates.

Complements djlint (HTML well-formedness) by loading every template through the
app's own Jinja environment: this compiles each one, catching Jinja syntax
errors, and proves each is discoverable by name. Together with StrictUndefined,
a missing variable or a missing partial fails a test instead of silently
rendering a blank.

``test_no_dead_templates`` additionally guards against orphaned template files:
every ``.html`` under app/web/templates must be reachable — either rendered by a
route (a ``"name.html"`` string in app/web/*.py) or pulled in by another template
via ``extends``/``include``/``import``/``from``. A template nothing references is
dead code and fails the test.
"""

import re
from pathlib import Path

from jinja2 import StrictUndefined

from app.web.routes import templates

_WEB_DIR = Path(__file__).resolve().parent.parent / "app" / "web"
_TEMPLATES_DIR = _WEB_DIR / "templates"

# Any quoted "something.html" token, in Python source or in Jinja tags. This is a
# deliberately broad net: it matches TemplateResponse(..., "auth/login.html"),
# {% extends "base.html" %}, {% from "components/ui.html" import ... %}, etc.
_TEMPLATE_REF = re.compile(r"""["']([\w./-]+\.html)["']""")


def test_strict_undefined_is_configured() -> None:
    # A typo'd or missing template variable must raise, not render blank.
    assert templates.env.undefined is StrictUndefined


def test_all_templates_compile() -> None:
    names = templates.env.list_templates(extensions=["html"])
    assert names, "no templates were discovered under app/web/templates"
    for name in names:
        # get_template parses/compiles the source; malformed {% %} raises here.
        templates.env.get_template(name)


def test_no_dead_templates() -> None:
    names = set(templates.env.list_templates(extensions=["html"]))
    assert names, "no templates were discovered under app/web/templates"

    # Collect every "*.html" reference across the web package: Python route
    # sources plus the templates themselves (extends/include/import/from). A file
    # mentioning its OWN name (e.g. ui.html documenting its import line in a
    # comment) doesn't count — reachability requires a reference from elsewhere.
    reachable: set[str] = set()
    for source in [*_WEB_DIR.rglob("*.py"), *_TEMPLATES_DIR.rglob("*.html")]:
        own_name = _template_name(source)
        reachable.update(
            ref for ref in _TEMPLATE_REF.findall(source.read_text()) if ref != own_name
        )

    dead = names - reachable
    assert not dead, (
        f"template(s) are never rendered or included by anything: {sorted(dead)}. "
        "Delete them, or reference them from a route/template."
    )


def _template_name(source: Path) -> str | None:
    """Return the name a template is referenced by, or None for a Python source.

    e.g. ``auth/login.html`` for a template file; ``None`` for any file outside
    the templates tree (such as a route module).
    """
    if _TEMPLATES_DIR in source.parents:
        return source.relative_to(_TEMPLATES_DIR).as_posix()
    return None
