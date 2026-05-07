from kiteconnect import KiteConnect

kite = KiteConnect(api_key='qzlyy9b8wnyijett')
with open('/home/ubuntu/access_token.txt') as f:
    kite.set_access_token(f.read().strip())

# Search across NSE indices
insts = kite.instruments('NSE')
for i in insts:
    sym = i['tradingsymbol'].upper()
    if 'MIDSMALL' in sym or 'MIDSML' in sym or 'MIDCAP' in sym or 'SMALLCAP' in sym:
        print(i['tradingsymbol'], i['instrument_token'], i['name'])
