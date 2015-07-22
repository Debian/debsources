Old patch tracker
================

Browsing
----------

* Package prefix
* Package
* Package / version

Views
----------

* View package summary (version, checksum, diff files,
  debian or upstream patches)
* View patch
* Syntax highlight using pygments
* Download patch


DB - caching
----------

* Storing package info (maintainer, uploader, name version, diff size,
  checksum, deb tar size checksum..), 
* Caching objects on disk (filterdiffs, diffgz) to reuse later

Patch formats
----------

* Quilt series
* Dpatch
* Cdbs

Misc
----------

* Export to UDD

TODO - Suggestions
----------

* The diffstat should link to anchors embedded in the diff for each file.
* Diff between orig.tar.gz for 3.0
* Different colors for co-maintained packages
* Extract comments from patch series to add in summary
* When viewing package list/versions or packages per maintainer it is 
  usefull to mention the packages that do not have patches. 
  (so people don't click for nothing)
* links to BTS for the closed bugs
* cross-distro solution?

Requirement Analysis
================

Target users
----------

* Debian developers / maintainers / contributors

* Upstream

* 3rd party distributions

Use stories
----------

[general - can be any of the 3 target users]

* As a patch tracker user I want to be able to browse by the prefix of packages
so that I can find specific packages.

    Acceptance criteria: - view list of package prefixes
                         - click on package prefix to find list of packages 
                         under that prefix

* As a patch tracker user I want to be able to search for a package to find its
patches.
    
    Acceptance criteria: - search form to input a package name
                         - get exact matches and other results

* As a patch tracker user I want to be able to browse between different versions
of each package to view patches in a specific version of a package.

    Acceptance criteria: - view package versions inside a package page 
                         - click on package version to find list of patches 
                         under that version

* As a patch tracker user I want to be able to view a patch with highlighted
syntax to track changed files and code.

    Acceptance criteria: - view patch in highlighted syntax

* As a patch tracker user I want to be able to download a patch in order to
apply it locally.

    Acceptance criteria: - raw download of the patch

* As a patch tracker user I want to be able to view the discription (if it
exists) of the patches in the list of a patches in order to identify the one I
am interested in.

    Acceptance criteria: - list description in the patches summary

* As a patch tracker user I want to be able to view the summary of a patch
(files changed) in the list of patches in order to identify the one I am
interested in.

    Acceptance criteria: - list changed files in the patches summary

* As a patch tracker user I want links pointing to Debsources from the modified
files mentioned in the description to view the source code.

    Acceptance criteria: - view links to Debsources from the changed files in
                         the patches summary

* As a patch tracker user I want links pointing to the bug tracker for the bugs
mentioned by the patches to view the origin of the bug.

    Acceptance criteria: - view link to BTS for the bugs mentioned in a patch


[Debian roles]

* As a Debian developer I want to view a patch applied in a package in order to
understand how a bug was resolved.

    Acceptance criteria: - view code and changes of a patch with highlighted
                         syntax

* As a Debian maintainer I want to download a patch applied in a package in
order to solve a bug present in a package I maintain.

    Acceptance criteria: - raw download of the patch


[Upstream]

* As an upstream author I want to be able to track changes between the
orig.tar.gz and the package in Debian.

    Acceptance criteria: - view diff of orig.tar.gz and Debian package
                         - download diff of orig.tar.gz and Debian package

* As an upstream author I want to be able to view the checksum of the
orig.tar.gz used in Debian so that I find out if there are any changes between
the released software and the one shipped by Debian.

    Acceptance criteria: - view checksum of the orig.tar.gz

* As an upstream author I want to be able to view a summary of changes (files
modified, number of lines etc) between orig.tar.gz and the package in Debian.

    Acceptance criteria: - view summary of all patches together

* As an upstream author I want to be able to download patches that solved bugs
in Debian that are still present in my release.

    Acceptance criteria: - raw download of patch


[3rd party distributions]

* As a contributor in another distribution I want to be able to view patches
applied in a package in Debian to fix bugs in the distribution I contribute.

    Acceptance criteria: - view patch in highlighted syntax

* As a contributor in another distribution I want to be able to download
patches applied in a package in Debian to apply it locally in my package.

    Acceptance criteria: - raw download of patch

Use cases
----------

Id: Case#1
Name: Navigate in the patch tracker
Actors: Patch tracker user, Debsources
Pre-conditions: User is at the index of the patch tracker
Normal flow:
1) The user will click on a package prefix
2) Debsources redirects the user to the page containing the list of packages
under that package prefix
3) The user will choose and click the package s/he is interested in
4) Debsources redirects the user to the list of versions of the package the user
selected
5) The user will select and click on a version
6) Debsources redirects the user to the specific page of that package - version
containing the basic information of that package, the summary of patches and the
list of patches.

Alternate flow:
1a) The user uses the search form to search for a package
    2) Debsources will find the exact matches and other results of that search
    3) Continue to the normal flow
1b) The user will choose to view the page with all the packages
    2) Debsources will redirect the user to a page where all the packages are
    listed
    3) Continue to the normal flow


Id: Case#2
Name: Download raw patch
Actors: Patch tracker user, Debsources
Pre-conditions: User is at the summary of a package
Normal flow:
1) The user will click on the download link of a specific patch
2) Debsources provides the user with the raw patch to save locally

Id: Case#3
Name: View a path
Actors: Patch tracker user, Debsources
Pre-conditions: User is at the summary of a package
Normal flow:
1) The user will select a patch applied by the Debian maintainer
2) Debsources redirects the user to the page containing the patch
3) Debsources highlights the syntax of the patch

Alternate flow:
1a) The user chooses an upstream patch
3a) The user disables Javascript and the user views a plain dump of the patch
without syntax highlighting

Id: Case#4
Name: View diff of orig.tar.gz and Debian package
Actors: Upstream author, Debsources
Pre-conditions: User is at the summary of a package
Normal flow:
1) The user will select a patch applied by the Debian maintainer
2) Debsources redirects the user to the page containing the patch
3) Debsources highlights the syntax of the patch

Alternate flow:
1a) The user chooses an upstream patch
3a) The user disables Javascript and the user views a plain dump of the patch
without syntax highlighting