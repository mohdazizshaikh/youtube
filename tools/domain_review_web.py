"""Run the opt-in private review console on literal IPv4 loopback only."""
import argparse
from pathlib import Path
import uvicorn
from app.domain_review_web import create_app, load_catalog


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,required=True)
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 1024<=args.port<=65535:
        parser.error('port must be between 1024 and 65535')
    app=create_app(args.db,load_catalog(args.catalog))
    uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False,proxy_headers=False)

if __name__=='__main__': main()
