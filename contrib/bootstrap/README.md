# Generating Bootstrap

We use bootstrap's customizer to ensure our bootstrap is the small and also
stays with the aesthetics of debian.

The file `config.json` contains related configuration.

## How To Generate

- Go to https://getbootstrap.com/customize/

- Upload the new `config.json` file, making sure you change the one in
  `/contrib/bootstrap` to match.

- Download the `bootstrap.zip` file

  ```sh
  BASE=/path/to/debsouces/repo # make sure this points to top level
  unzip ~/Downloads/bootstrap.zip -d /tmp # Download location may vary
  mv /tmp/js/bootstrap.min.js /tmp/css/bootstrap.min.css $BASE/debsources/app/static/bootstrap
  ```

- Remove unchanged vars from `config.json` and place in folder.
  ```sh
  $EDITOR /tmp/config.json
  mv /tmp/config.json  $BASE/contrib/bootstrap
  ```
