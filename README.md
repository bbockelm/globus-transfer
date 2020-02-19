# globus-transfer

## Installation

To install the tool, run (from your shell)
```sh
python3 -m pip install --user --upgrade git+https://github.com/JoshKarpel/globus-transfer.git
```

If this fails, you may need to [install Python 3 and `pip` from your system package
manager](https://realpython.com/installing-python/),
or use something like [miniconda](https://docs.conda.io/en/latest/miniconda.html)
to set up a personal Python environment.

After installation, you should be able to run
```sh
globus --help
```
To see the help message.

To update the tool, run the same command as you did to install it above.


## Development

### Get a Client ID

We shouldn't need to do this again, but just in case...

1. Go to https://developers.globus.org/
2. Select "Register your app with Globus".
3. Enter a project name (e.g. "globus-transfer") and contact email.
4. Open the "Add..." drobdown on the project you made and select "Add new app".
5. Enter an app name (e.g. "globus-transfer"). 
   Check the "native app" box.
   Select the scopes `openid`, `profile`, `email`, and `urn:globus:auth:scope:transfer.api.globus.org:all`.
   Add a redirect line containing `https://auth.globus.org/v2/web/auth-code`.
   Click "Create App".
6. Copy the Client ID from this screen. It is not secure information.


