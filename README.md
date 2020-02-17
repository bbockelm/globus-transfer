# globus-transfer

## Get a Client

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


