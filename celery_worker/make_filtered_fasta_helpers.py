#!/usr/bin/env python3

# make_filtered_fasta.py
#
# python-only implementation of the previous collection of python+bash scripts
# implements mongo queries using the aggregate framework (concurrently). No multiprocessing. 
# Tested 2x faster on wl-cmadmin, ~20x faster on my laptop

import os
import re
import glob
import argparse
from pymongo import MongoClient
from pymongo import version_tuple as pymongo_version
# global SeqDB
# global ProtDB
# global sequest

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i+n]

def run(host=None, 
        port=None, 
        mongodb_uri=None, 
        seqdb_name='SeqDB_072114', 
        seqdbcoll='SeqDB_072114', 
        protdb_name='ProtDB_072114', 
        protdbcoll='ProtDB_072114', 
        sequest=True, 
        cwd=None, 
        ):

    if cwd:
        # change current working directory
        os.chdir(cwd)

    if host and port:
        client = MongoClient(host, port)
    elif not mongodb_uri:
        default_mongodb_uri = ','.join(('imsb0501:27018', 
                                        'imsb0515:27018', 
                                        'imsb0601:27018', 
                                        'imsb0615:27018', 
                                        'node0097:27018', 
                                        'node0113:27018', 
                                        'node0129:27018', 
                                        'node0145:27018', 
                                        'node0401:27018', 
                                        'node0411:27018', 
                                        'node0421:27018', 
                                        'node0431:27018', 
                                        'node0441:27018', 
                                        'node0451:27018', 
                                        'node0461:27018', 
                                        'node0471:27018', 
                                        'node0481:27018', 
                                        'node0491:27018', 
                                        'node0501:27018', 
                                        'node0511:27018', 
                                        'node0521:27018', 
                                        'node0531:27018', 
                                        'node0541:27018', 
                                        'node0551:27018', 
                                        'node0561:27018', 
                                        'node0571:27018', 
                                        'node0581:27018', 
                                        'node0591:27018', 
                                        'node0601:27018', 
                                        'node0617:27018', 
                                        'node0633:27018', 
                                        'node0649:27018', 
                                        'node0665:27018', 
                                        'node0681:27018', 
                                        'node0922:27018', 
                                        'node0937:27018', 
                                        'node0953:27018', 
                                        'node0969:27018', 
                                        'node0985:27018', 
                                        'node1001:27018', 
                                        'nodea1301:27018', 
                                        'nodea1331:27018', 
                                        'nodea1401:27018', 
                                        'nodea1431:27018', 
                                        ))
        mongodb_uri = 'mongodb://'+default_mongodb_uri
        client = MongoClient(mongodb_uri)
    else:
        client = MongoClient(mongodb_uri)
    SeqDB = client[seqdb_name][seqdbcoll]
    ProtDB = client[protdb_name][protdbcoll]

    output_filename = 'output.fasta'
    peptides = set(first_match_producer())
    print(list(peptides)[:10])
    print(str(len(peptides)) + ' peptides')
    # 200k should be a conservative estimate to avoid reaching max BSON size
    parent_proteins = set()
    for peptide_chunk in chunks(list(peptides), 200000): 
        seqdb_aggregate = SeqDB.aggregate([{'$match': {'_id':{'$in':peptide_chunk}}},
                             {'$unwind' : '$p'},
                             {'$group': {'_id': None, 'p': {'$addToSet': '$p.i'}}}], allowDiskUse = True)
        if pymongo_version[0] == 3:
            parent_proteins.update(next(seqdb_aggregate)['p'])
        else:
            parent_proteins.update(seqdb_aggregate['result'][0]['p'])
    
    print(str(len(parent_proteins)) + ' proteins')
    
    with open(output_filename,'w') as f:
        count = 0
        for protein_chunk in chunks(list(parent_proteins), 500000):
            protdb_query = ProtDB.find({'_id':{'$in': protein_chunk}}, {'s': True, 'd': True})
            for query in protdb_query:
                f.write(construct_fasta_record(query))
                count += 1
    print('Wrote {} FASTA records to {}'.format(count, output_filename))
    if sequest:
        make_sequest_params(output_filename)

    return True

def first_match_producer():
    ''' generator function that returns peptides from "M 1" lines from 
    all SQT files in the current working directory'''
    for sqt_file in glob.glob('*.sqt'):
        with open(sqt_file) as f:
            for line in f:
                if line.startswith('M\t1'):
                    try:
                        #skip incomplete lines
                        peptide = line.split('\t')[9]
                    except IndexError:
                        print("incomplete line: " + peptide)
                        continue
                    peptide = peptide[peptide.index('.')+1:peptide.rindex('.')]
                    yield strip_ptms(peptide) if '(' in peptide else peptide
                        
def strip_ptms(peptide):
    #peptide = "KVG(42.010565)VIFRLIQ(123.234)LVVLVYV(42.010565)IGGR"
    for match in re.findall('\((.*?)\)',peptide):
        peptide = peptide.replace(match,'')
    peptide = peptide.replace('(','')
    peptide = peptide.replace(')','')
    return peptide

def construct_fasta_record(query):
    ''' return FASTA-formatted string from ProtDB query '''
    if query['d'].startswith('Reverse_'):
        fasta_record = '>Reverse_'+str(query['_id'])+'\n'+query['s']+'\n'
    else:
        fasta_record = '>'+str(query['_id'])+'\n'+query['s']+'\n'
    return fasta_record

def make_sequest_params(output_filename):
    with open('sequest.params', 'w') as f:
        f.write('[SEQUEST]\n')
        f.write('database_name = {}/{}\n'.format(os.getcwd(), output_filename))
    print('Created sequest.params file')

def main(cwd, seq_db = 'SeqDB_072114', seqdbcoll = 'SeqDB_072114', prot_db = 'ProtDB_072114', protdbcoll = 'ProtDB_072114',
         mongohost = 'wl-cmadmin', mongoport = 27018, write_sequest = True, **kwargs):
    # note: additional kwargs are discarded
    os.chdir(cwd)
    client = MongoClient(mongohost, mongoport)
    global SeqDB
    SeqDB = client[seq_db][seqdbcoll]
    global ProtDB
    ProtDB = client[prot_db][protdbcoll]
    global sequest
    sequest = write_sequest
    #print(SeqDB.find_one())
    run()

# *****************
if __name__ =='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seqdb', help='MongoDB SeqDB Database name', type=str, default='SeqDB_072114')
    parser.add_argument('--seqdbcoll', help='MongoDB SeqDB Collection name', type=str, default='SeqDB_072114')
    parser.add_argument('--protdb', help='MongoDB ProtDB Database name', type=str, default='ProtDB_072114')
    parser.add_argument('--protdbcoll', help='MongoDB ProtDB Collection name', type=str, default='ProtDB_072114')
    parser.add_argument('--host', help='MongoDB host', type=str)
    parser.add_argument('--port', help='MongoDB port', type=int)
    parser.add_argument('-s', '--sequest', help='Create sequest.params file using path to new FASTA file', action='store_true')
    args = parser.parse_args()

    if args.host and args.port:
        client = MongoClient(args.host, args.port)
    else:
        default_mongodb_uri = ','.join(('imsb0501:27018', 
                                        'imsb0515:27018', 
                                        'imsb0601:27018', 
                                        'imsb0615:27018', 
                                        'node0097:27018', 
                                        'node0113:27018', 
                                        'node0129:27018', 
                                        'node0145:27018', 
                                        'node0401:27018', 
                                        'node0411:27018', 
                                        'node0421:27018', 
                                        'node0431:27018', 
                                        'node0441:27018', 
                                        'node0451:27018', 
                                        'node0461:27018', 
                                        'node0471:27018', 
                                        'node0481:27018', 
                                        'node0491:27018', 
                                        'node0501:27018', 
                                        'node0511:27018', 
                                        'node0521:27018', 
                                        'node0531:27018', 
                                        'node0541:27018', 
                                        'node0551:27018', 
                                        'node0561:27018', 
                                        'node0571:27018', 
                                        'node0581:27018', 
                                        'node0591:27018', 
                                        'node0601:27018', 
                                        'node0617:27018', 
                                        'node0633:27018', 
                                        'node0649:27018', 
                                        'node0665:27018', 
                                        'node0681:27018', 
                                        'node0922:27018', 
                                        'node0937:27018', 
                                        'node0953:27018', 
                                        'node0969:27018', 
                                        'node0985:27018', 
                                        'node1001:27018', 
                                        'nodea1301:27018', 
                                        'nodea1331:27018', 
                                        'nodea1401:27018', 
                                        'nodea1431:27018', 
                                        ))
        mongodb_uri = 'mongodb://'+default_mongodb_uri
        client = MongoClient(mongodb_uri)
    SeqDB = client[args.seqdb][args.seqdbcoll]
    ProtDB = client[args.protdb][args.protdbcoll]
    sequest = args.sequest

    run()