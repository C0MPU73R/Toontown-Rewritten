# While dev.prc contains settings for both the dev server and client, the
# live server separates these. The client settings go in config/public_client.prc
# and server settings go here. Don't forget to update both if necessary.

# Server settings
want-dev #f
want-cheesy-expirations #t

# Shared secret for CSMUD
# ##### NB! Update config/public_client.prc too! #####
csmud-secret Yv1JrpTUdkX6M86h44Z9q4AUaQYdFnectDgl2I5HOQf8CBh7LUZWpzKB9FBD

# ODE isn't ready yet :(
want-golf #f

# Beta Modifications
# Temporary modifications for unimplemented features go here.
want-sbhq #t
want-cbhq #t
want-lbhq #t
want-bbhq #f
want-pets #f
want-old-fireworks #t
want-parties #f
want-accessories #f
