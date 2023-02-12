"""
This module is part of the preprocessing. It takes the full-corpus.xml file and replaces all problematic items in the text.
"""


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="Replace unwanted characters in wimcor before preprocessing.")
    parser.add_argument('path', metavar='P', type=str, help='path/to/wimcor')
    args = parser.parse_args()

    with open(f'{args.path}/full-corpus.xml', 'r') as input_file, \
            open(f'{args.path}/full-corpus-reformatted.xml', 'w') as output_file:
        while 1:
            for lines in range(206100):
                line = input_file.readline().replace('&', '&amp;')
                line = line.replace('<<', '<')
                line = line.replace('<5>', '')
                line = line.replace('(<', ' &lt;')
                line = line.replace('(>', ' &gt;')
                line = line.replace(' <', ' &lt;')
                line = line.replace('> ', '&gt; ')
                line = line.replace('< ', '&lt; ')
                line = line.replace('< ', '&lt; ')
                line = line.replace(' >', ' &gt;')
                line = line.replace('<*', '&lt;*')
                line = line.replace('>*', '&gt;*')

                line = line.replace('sample&gt;', 'sample>')
                line = line.replace('&lt;sample', '<sample')
                line = line.replace('pmw&gt;', 'pmw>')
                line = line.replace('&lt;pmw', '<pmw')

                output_file.write(line)
            break


if __name__ == "__main__":
    main()
