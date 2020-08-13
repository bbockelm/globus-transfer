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

To update the tool to the latest version, run `globus upgrade`.

## Usage Examples

For complete help (including exhaustive option information), see `globus --help` or `globus <command> --help`.

### Start a New Transfer

We'd like to transfer a file located at `~/file`
and a directory (with all of its contents) at `~/dir` on `endpoint_a` to
the same paths on `endpoint_b`.

```sh
$ globus transfer endpoint_a endpoint_b '~/file':'~/file' '~/dir/':'~/dir/'
a80aeb52-5271-11ea-ab5b-0a7959ea6081
```

The trailing slashes indicate the directory transfers, while those without are
file transfers. The resulting `task_id` is written to stdout.

### Wait for a Transfer to Complete

Now that we've submitted a transfer, we'd like to wait for it to finish so that
we know it's safe to start whatever comes next.

```sh
$ globus wait a80aeb52-5271-11ea-ab5b-0a7959ea6081 --timeout 120
```

### List Transfer Event History

```sh
$ globus history
task_id                               label    status                            source_endpoint                                                  destination_endpoint                             completion_time
a80aeb52-5271-11ea-ab5b-0a7959ea6081         SUCCEEDED  u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7                        discovery#mir-globus1                        2020-02-18 17:11:13+00:00
781f57d4-5271-11ea-b978-0e16720bb42f         SUCCEEDED  u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7                        discovery#mir-globus1                        2020-02-18 17:09:52+00:00
036d0cc4-5271-11ea-ab5b-0a7959ea6081         SUCCEEDED  u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7                        discovery#mir-globus1                        2020-02-18 17:06:37+00:00
eca13eac-5270-11ea-971b-021304b0cca7           FAILED   u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7                        discovery#mir-globus1                        2020-02-19 15:49:49+00:00
c7e502a6-5270-11ea-971b-021304b0cca7         SUCCEEDED  u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7                        discovery#mir-globus1                        2020-02-18 17:04:57+00:00
a973a4a8-5270-11ea-971b-021304b0cca7           FAILED                         discovery#mir-globus1                        u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7  2020-02-19 15:49:51+00:00
473aabce-5270-11ea-ab5b-0a7959ea6081           FAILED                         discovery#mir-globus1                        u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7  2020-02-19 15:49:52+00:00
3d649eb6-5270-11ea-b978-0e16720bb42f           FAILED                         discovery#mir-globus1                        u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7  2020-02-19 15:52:24+00:00
2971019c-4f41-11ea-b975-0e16720bb42f         SUCCEEDED  u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7                                 None                                2020-02-14 15:46:29+00:00
240d99c2-4f41-11ea-b975-0e16720bb42f         SUCCEEDED                        discovery#mir-globus1                                                       None                                2020-02-14 15:46:20+00:00
7146b3c2-4dd4-11ea-b974-0e16720bb42f         SUCCEEDED                        discovery#mir-globus1                        u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7  2020-02-12 20:15:45+00:00
63c325aa-4dd4-11ea-ab5a-0a7959ea6081           FAILED                         discovery#mir-globus1                        u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7  2020-02-12 20:15:52+00:00
607dd232-4dd4-11ea-ab5a-0a7959ea6081           FAILED                         discovery#mir-globus1                        u_dvi6jhvpmrdzbdyxf7f4hczmcy#1d91f868-4de4-11ea-971a-021304b0cca7  2020-02-12 20:15:53+00:00
```

## Development

To get a development environment:
1. Clone this git repository locally.
2. Enter the repository root directory and run `python3 -m pip install --user -e .` (a "local", "editable" `pip` install)

Now you should be able to run the `globus` command locally.
Any edits you make to the `globus.py` file will be reflected immediately.
If you make changes to `setup.py`, you will need to rerun the install command.

### Get a Client ID

We shouldn't need to do this again
(this ID is associated with the application, not an individual user),
but just in case...

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
