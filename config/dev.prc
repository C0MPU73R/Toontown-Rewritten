# This is the PRC configuration file for developer servers and clients. 
# If making a change here, please remember to add it to public_client.prc
# as well as deployment/server.prc if necessary.

# Client settings
window-title Toontown Rewritten [DEV BUILD]
server-version dev
sync-video #f
want-dev #f


# Resource settings
vfs-mount resources/phase_3 /phase_3
vfs-mount resources/phase_3.5 /phase_3.5
vfs-mount resources/phase_4 /phase_4
vfs-mount resources/phase_5 /phase_5
vfs-mount resources/phase_5.5 /phase_5.5
vfs-mount resources/phase_6 /phase_6
vfs-mount resources/phase_7 /phase_7
vfs-mount resources/phase_8 /phase_8
vfs-mount resources/phase_9 /phase_9
vfs-mount resources/phase_10 /phase_10
vfs-mount resources/phase_11 /phase_11
vfs-mount resources/phase_12 /phase_12
vfs-mount resources/phase_13 /phase_13
model-path /
default-model-extension .bam

# Server settings
eventlog-host 127.0.0.1
accountdb-local-file databases/csm-cookies.db
account-server-endpoint https://www.toontownrewritten.com/api/gameserver/


# DC Files
# This is, oddly enough, in *reverse* order of their loading...
dc-file config/toon.dc
dc-file config/otp.dc


# Beta Modifications
# Temporary modifications for unimplemented features go here.
want-pets #f
want-news-tab #f
want-news-page #f
want-old-fireworks #t
# This is a temporary 'fix' for DistributedSmoothNodes... probably not the permanent solution to our problem, but it works for now.
smooth-lag 0.4


# Developer Modifications
# A few fun things for our developer build. These shouldn't go in public_client.
estate-day-night #t
want-instant-parties #t
show-total-population #f
want-whitelist #f


# Holidays and Events
force-holiday-decorations 6
