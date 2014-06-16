Local Information
=================

You can customize a Debsources instance to publish on the web local
information, such as news, instance-specific information, etc.  To do so you
should create files containing HTML snippets in the *local directory* of your
Debsources instance, which by default is located at `$DEBSOURCES_ROOT/local/`.

You can customize the path of your local directory in `config.ini` as follows:

	[DEFAULT]
	# ...
	local_dir: /some/where/else    # defaults to: %(root_dir)s/local
	# ...

At present, you can add the following kind of local information to your
Debsources instance:

- **news on the stats page**, by creating a `news.stats.html` file. Ideally,
  the file should contain a single HTML list, e.g., `<ul>...</ul>`

- **credits** in the bottom right of the footer, by creating a `credits.html`
  file. Ideally, the file should contain something small like a logo, e.g.,
  `hosted by <a href=""><img>...</img></a>`
