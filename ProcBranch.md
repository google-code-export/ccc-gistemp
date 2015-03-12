# Introduction #

This document describes the procedure for creating a development branch in the subversion repository for the ccc-gistemp project.

# Details #

Branches are named `svn/branches/YYYY-MM-DD/branchshortname`, where YYYY-MM-DD is the date that the branch is created in ISO 8601 format (for today, it would be 2011-05-17), and _branchshortname_ is a convenient short name for your branch (for example, "pypy" would be reasonable for PyPy development).

The parent directory of the branch, `svn/branches/YYYY-MM-DD`, has to be created first.  If there are more than one branches being created on the same day then this may be already created.

In order to create the parent directory:

```
# Creates a "branches" directory of your local disk:
svn co https://ccc-gistemp.googlecode.com/svn/branches --depth empty
cd branches
# Be sure to substitute the actual date here:
mkdir 2011-05-17
svn add 2011-05-17/
svn ci
```

Give a reason like "Adding directory in preparation for creating branch".

Now create the branch using a subversion copy command (when I did this, I had to use the "--username" option to specify my googlecode user id):

```
# Be sure to substitude the actual full branch name here:
svn copy https://ccc-gistemp.googlecode.com/svn/trunk https://ccc-gistemp.googlecode.com/svn/branches/2011-05-17/scratch
```

That's it.  Hopefully.