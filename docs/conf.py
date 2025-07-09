import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'OpenFactory'
author = 'OpenFactory contributors'
copyright = '2025, OpenFactory contributors'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx_autodoc_typehints',
    'sphinx.ext.napoleon',
    'myst_parser',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'pydata_sphinx_theme',
    'sphinx_design',
]

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_rtype = False

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable/', None),
}

nitpick_ignore = [
    ('py:exc', 'docker.errors.APIError'),
    ('py:exc', 'docker.errors.NotFound'),
    ('py:class', 'asyncua.Client'),
    ('py:class', 'cimpl.Producer'),
    ('py:class', 'pydantic.main.BaseModel'),
    ('py:class', 'pydantic.root_model.RootModel[Dict[str, Node]]'),
    ('py:class', 'pydantic.root_model.RootModel[Dict[str, Union[Volume, NoneType]]]'),
    ('py:class', 'pydantic.root_model.RootModel[Dict[str, Optional[Volume]]]'),
    ('py:class', "pydantic.root_model.RootModel[Dict[str, Union[Literal['ANY'], str, List[str]]]]"),
    ('py:exc', 'pydantic.ValidationError'), 
]

templates_path = ['_templates']
html_css_files = ['custom.css']
exclude_patterns = []
master_doc = "index"

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']

html_theme_options = {
    "logo": {
        "text": "OpenFactory",
    },
    "navbar_end": ["theme-switcher", "navbar-icon-links"],  # <-- enable switch button
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory",
            "icon": "fab fa-github",
            "type": "fontawesome",
        },
    ],
    "show_prev_next": False,
    "show_toc_level": 2,
    "use_edit_page_button": True,
}

html_context = {
    "github_user": "Demo-Smart-Factory-Concordia-University",
    "github_repo": "OpenFactory",
    "github_version": "main",
    "doc_path": "docs",
}

html_show_sourcelink = False

autodoc_default_options = {
    'members': True,                # Include all documented class/module members
    'special-members': '__init__',  # Include __init__ method in class docs
    'show-inheritance': True,       # Show base classes in class documentation
}
