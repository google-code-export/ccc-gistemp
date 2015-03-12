# Introduction #

Coding standards are necessary to preserve everyone's sanity on a shared software project.


# Standards #

Please be: Clear; Simple; Conservative.  Avoid optimisation.

Coding in Python is preferred.  Avoid other languages where possible.

## Python ##

[PEP 8](http://www.python.org/dev/peps/pep-0008/) applies.  A very brief summary of which is: 4 space indent (no tabs); 79 columns; one import per line; no white-space before colons; newline immediately after a colon.

All Python code should run on a Python 2.4 system (see "Please be conservative", above).  So do not use newer features.  Read the [Python 2.4 documentation](http://www.python.org/doc/2.4.4/) to avoid accidentally using newer features.  But be aware that Python may actually be run using a newer Python version.  So do not use anything that changes in a later version (I don't know of anything important off-hand, but obviously anything deprecated is right out).

(In particular regarding Python 2.4 compatible code:) «x if c else y» (Python's ternary expression) is not allowed, because it is Python 2.5.

Avoid non-standard extensions.  Sadly this means no numpy, no PIL.  For now.

Python files should start with a #! line then the keywords junk for our SCM (currently, subversion), and basic identification:

```
#!/usr/bin/env python
# $URL$
# $Rev$
#
# foo.py
#
# Joe Bloggs, Affiliated Co, YYYY-MM-DD
```

The name is so that we know who to ask when we have a question.  The affiliation is optional, leave it off if you don't want your company/organisation associated with the work.  The date should be the data of creation or last major revision (detailed revision data is kept in SCM and should _not_ be recorded here).

(We should probably have a copyright notice somewhere;  in general the copyright will be owned by whoever wrote the code.)

Following the header comment there should be a description of the program.  Generally this should be inside a Python doc string (this is the string that is printed out when you go: «import foo;help(foo)»).

In general Python files should be executable and should run tests when executed, unless they actually implement a command line tool.

### Things PEP 8 doesn't mention ###

No tabs.  Ever.

Prefer `[0] * 12` and `'abc' * 10` over `12 * [0]`.  In other words sequence on left, number on right.  This is a completely arbitrary choice so drj just picked one (the one that drj does by habit, as it happens).

### import ###

(one per line, see PEP 8)

The line previous to an import statement should be a comment that refers to the documentation for the module.  Try and find a reference to the exact version of the documentation you were reading when you used the module.  So prefer http://www.python.org/doc/2.4.4/lib/module-urllib.html over http://www.python.org/doc/lib/module-urllib.html .  Referencing the particular version of the documentation means that we know which version of the module you were programming against (and hence what dependencies and assumptions have been made).

Avoid `from foo import *`.

An import that is local to a function is okay (this is actually a violation of PEP 8, which says all imports must go at the top of file, but I quite like it.  Discuss).


### Documenting Code ###

We plan to use [Epydoc](http://epydoc.sourceforge.net/) to extract API
documentation from Python code. This primarily uses docstrings, but also used
special comments to document things like global variables.

For docstrings [PEP257](http://www.python.org/dev/peps/pep-0257/) generally
applies. However, the details of how docstring content is formatted and marked
up take advantage of the [Epydoc](http://epydoc.sourceforge.net/) features.

[Epydoc](http://epydoc.sourceforge.net/) supports a number of markup styles;
for CCC code we will use reStructuredText (RST), which is defined at
[Docutils](http://epydoc.sourceforge.net/).

The general rules are follow here, but for all the details of how to document
with [Epydoc](http://epydoc.sourceforge.net/) see
[using Epydoc syntax for API documentation](EpydocSyntax.md).


#### What Should be Documented ####

Pretty much everything public. In other words, if it does not start with an
underscore then you probably should document it; or consider making it
private. Things to document include:

  * The module itself in a docstring at the top of the file.
  * All top level public functions within a module.
  * All top level public classes within a module, including exceptions.
  * All public methods of a class.
  * All public attributes of a class.
  * All public properties of a class.
  * All public global variables within a module.

With well documented source code we will be able to produce reference material
something like this
[example generated documentation](http://www.ollis.eclipse.co.uk/index.html).
Note: This is just an example. I have taken
liberties with some CCC module to generate this.


## Fortran, C, /bin/sh ##

Avoid these where possible.  Since 2010, they are no longer used by ccc-gistemp.