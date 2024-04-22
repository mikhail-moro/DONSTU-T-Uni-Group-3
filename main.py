import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=str, choices=['server', 'client'])
    args = parser.parse_args()

    if args.run == 'client':
        from client.client import run
        run()
    elif args.run == 'server':
        from server.server import run
        run()
    else:
        raise ValueError()
