class ToontownRPCHandler:
    def __init__(self, air):
        self.air = air

    def rpc_ping(self, request, data):
        """For testing purposes: This just echos back the provided data."""
        return data

    def rpc_getGSIDByAccount(self, request, accountId):
        """Gets the GSID for a given webserver account ID, or null if invalid."""
        account = self.air.mongodb.astron.objects.find_one(
            {'dclass':'Account', 'fields.ACCOUNT_ID': accountId})

        if account:
            return account['_id']

    def rpc_getAccountByGSID(self, request, gsId):
        """Gets the account ID associated to a particular GSID, or null if invalid."""
        account = self.air.mongodb.astron.objects.find_one({'_id': gsId})

        if account and account.get('dclass') == 'Account':
            return account.get('fields',{}).get('ACCOUNT_ID')

    def rpc_getAvatarsForGSID(self, request, gsId):
        """Gets the set of avatars (Toons) that exist on a given gsId, or null if invalid."""

        def callback(dclass, fields):
            if dclass is None:
                return request.result(None)

            if dclass.getName() is None:
                return request.result(None)

            request.result(fields.get('ACCOUNT_AV_SET'))

        self.air.dbInterface.queryObject(self.air.dbId, gsId, callback)

        return request
