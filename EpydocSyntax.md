# Introduction #

This page is intended to provide a guide to writing complete API documentation
using the syntax supported by [Epydoc](http://epydoc.sourceforge.net/).

Generally guidance is provided by lots of examples rather than trying to specify
things too formally.

The style of markup used is reStructuredText, see
[Docutils](http://epydoc.sourceforge.net/) for full details. This guide does not
try to provide much information about reStructuredText, except for the special
ways that [Epydoc](http://epydoc.sourceforge.net/) uses it. The
[reStructuredText primer for coders](MiniRstPrimer.md) page provides an introduction.


## Modules ##

The module's documentation is defined in its docstring at the top of the
source file. A semi-realistic example follows:

```
#!/usr/bin/env python
# $Id: //info.ravenbrook.com/project/ccc/version/0.1/code/fort.py#1 $
"""Support for Python/Fortran interworking.

This module provides support for writing Python modules and programs that need
to interwork with Fortran in various ways.

The main thing this module provides is the `File` class, which supports access
to unformatted files; a binary file format.

The other main feature is the `unpackRecord` function, which can be useful
during the initial stages of converting a Fortran program to reasonably simliar
looking Python code.

"""
__docformat__ = "restructuredtext"
```

This example introduces some general rules.

> The docstring should start with a short summary, which should be a single
> sentence; aim to fit it on a single line. This string is typically used
> documentation by tools to provide a summay, separate from the full
> documentation.

> There should be a blank line before the closing (triple) quotes.

> You always need the `__docformat__ = "restructuredtext"` line, which
> should normally immediately follow the docstring. (Without this,
> [Epydoc](http://epydoc.sourceforge.net/) will not correctly interpret the
> documentation markup.)

The other notable items are the names surrounded by backquote characters. for
example ```File```. These are references to other documented items within
the module. Generated documentation can turn such references into hypertext
links.

Global variables should be documented with special comments, which begin with
a hash, colon and space. For example:

```
#: The type of platform we are running on.
#
#: This is a string and can be one of:
#:
#: - "linux"
#: - "osx"
#: - "windows"
#: - "unknown"
#:
#: It get set when the module is loaded and should be treated as read-only.
platformType = "unknown"
```

Often a single summary line is sufficent. Otherwise follow the summary +
detail pattern.


## Functions ##

Using a semi-realistic example, based on the `fort` module.

```
def open(name, mode='rb'):
    """Open a binary Fortran file.

    Opens a file and wraps it as a `File` instance, ready for access in Fortran
    binary mode.

    :Param name:
        The path of the file to be opened.
    :Param mode:
        The file's access mode, as per the builtin open function. The default
        is 'rb' and **must** always include 'b'.
    :Return:
        A `File` instance for the newly opened file.

    """
    assert 'b' in mode
```

This introduces some new features.

> There is a special syntax used to describe the arguments and return value.
> These are actually using the reStructuredText **field list** syntax,
> (see the [reStructuredText primer for coders](MiniRstPrimer.md) for more
> details), but [Epydoc](http://epydoc.sourceforge.net/) peforms extra
> processing to interpret certain fields specially.

Notice that the function documentation can put links to other functions,
classes, etc; the `File` class in this example.


### More on Documenting Function Args and Returns ###

Some rules:

> Normally list the arguments in the order they appear in the function
> signature.

> Closely related arguments can (and should) appear together, as in:

```
    :Param x, y:
        The coordinates of the point.
```

> If the function has no return value then **do not** include a
> `:Return:` field.

To document a function that takes variable arguments and keyword arguments
do this sort of thing:

```
def flexible(x, *args, **kwargs):
    """A flexible function.

    :Param x:
        The X value.
    :Param args:
        Further position arguments are additional coordinates.
    :Param kwargs:
        All the standard flexible keyword arguments are handled.
        See the `FlexFunc` module.
    :Kwarg very:
        If a ``True`` value then be even more flexible.
    :Kwarg rigid:
        If a ``True`` value try to be a bit less flexible.
    """
```


## Classes ##

Once again a semi-realistic example, based on the `fort` module.

```
class File(object):
    """A Fortran binary (unformatted) file object.

    A binary Fortran file can be opened using the open method of this module;
    a File object is returned that supports a writeline method (for writing
    records), a readline method (for reading records) and the iterator
    protocol (for reading).

    It is normally easier to use the `open` factory function rather than
    construct instances directly.

    """
    #: The number of bytes in the natural word size used in the file.
    w = 4
```

The docstring of the class describes what the class is for and, for suitable
complex classes should give guidance on how to use it.

All public methods are documented in exactly the same way as module functions.
Do not include `self` in the documented arguments.

For class attributes it is preferable to use the special comment form to
document them, as for `w` in the above example. For instance attributes
it is better to use `:Ivar:` fields (this keeps the constructor code less
cluttered and works for instance variables that are not defined in the
constructor). For example:

```
class Coord2D(object):
    """A single 2 dimensional cartesian coordinate.

    :Ivar x, y:
        The coordinates, stored as floating point values.
    """
```


## Exceptions ##

Exceptions should always be classes and should always have the builtin
`Exception` as a base class. Generally, you should document them as you would
any other class. The description should, of course, describe the general
conditions under which the exception is raised.

When you document functions and methods, you can (and should) indicate which
exceptions can be raised.

```
def readline(self) :
    """Read a single binary record as a string.

    ...

    :Raises FileFormatError:
        If the record has mismatching record length prefix and suffix
        markers.
    :Raises FileTruncatedError:
        If the file did not apparently contain a complete record.
    """
```

Exceptions should be automatically cross-referenced when in
a `:Raises ...:` field. Otherwise you can explicitly reference them as in:

```
:Raises FileTruncatedError:
    If the record has mismatching record length prefix and suffix
    markers. This can sometime mask an underlying `FileFormatError`.
```