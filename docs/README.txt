# Documentation of OpenFactory
This folder contains the coniguration files to create the documetnation on Read The Docs.

To test locally the documentation, create it using
```bash
sphinx-build -b html docs docs/_build/html -nWT -v
```

To view it run a local webserver like so:
```bash
python -m http.server 8000 -d docs/_build/html
```
