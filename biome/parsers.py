#!/usr/bin/env python3

import re
from itertools import chain

def per_to_float(x):
    '''
    '50%' -> 0.50
    '''
    return float(x[:-1])/100
    
def dtaselect_json(in_file, noProtDB=True, small = False, get_tax=False, get_forward_loci=False, 
                      check_peptides=False, get_hashes=False, return_reverse=True):

    ''' steps through and parses a DTASelect-filter.txt file (generator function) 
        if small: get rid of keys: 'loci' and 'peptides'
        if get_tax: Look up taxonomy information for each protDB ID
        if get_forward_loci: Don't trust DTASelect's list of protDBs (for each locus)
        if check_peptides: Check if all peptide sequences are in all proteins sequences in 'forward_loci'
        if return_reverse: include reverse loci
                  
    '''

    if get_tax:
        from pymongo import MongoClient
        client = MongoClient('wl-cmadmin', 27017)
        taxDB = client.taxDB.taxDB
        import taxonomy
        t = taxonomy.Taxonomy()
    
    if get_forward_loci:
        from itertools import chain
        from pymongo import MongoClient
        seqDB = MongoClient('wl-cmadmin', 27018).SeqDB_072114.SeqDB_072114
        
    if check_peptides:
        # According to stack overflow, python doesn't waste time importing things twice
        from pymongo import MongoClient
        protDB = MongoClient('wl-cmadmin', 27018).ProtDB_072114.ProtDB_072114
        
    if get_hashes:
        from pymongo import MongoClient
        client = MongoClient('wl-cmadmin', 27017)
        redunDB = client.redunDB.redunDB

    with open(in_file) as f:
        line = next(f)
        
        # Skip header. Todo: parse it
        while line.startswith('Locus') == False:
            line = next(f)
        
        # Read locus header
        locus_columns = line.strip().split('\t')
        locus_types = [str, int, int, per_to_float, int, int, float, str, float, float, str]
        
        # Read peptide header
        line = next(f)
        peptide_columns = line.rstrip().split('\t')
        peptide_types = [str, str, float, float, float, float, float, float, int, float, float, int, str]
        line = next(f)
        
        # Read the rest of the file
        while line != '\tProteins\tPeptide IDs\tSpectra\n':
            protein = dict()
            # Read loci for a protein
            loci = []
            # while len(re.findall('^[0-9]', line))>0 or line.startswith('Rev'): # While it starts with a number or "Rev'
            while not line.startswith('\t') and not line.startswith('*'): # While it starts with a number or "Rev'
                loci.append(dict(zip(locus_columns, [x(y) for x,y in zip(locus_types, line.strip().split('\t'))])))
                line = next(f)
            
            # Read peptides
            peptides = []
            while line[0] in ['\t', '*'] and line != '\tProteins\tPeptide IDs\tSpectra\n':
                peptides.append(dict(zip(peptide_columns, [x(y) for x,y in zip(peptide_types, line.rstrip().split('\t'))])))
                line = next(f)
            
            protein['peptides'] = peptides
            protein['loci'] = loci
            
            # some convenience functions
            # Parse out reverse loci
            for l in protein['loci']:
                if l['Locus'].startswith('Reverse_'):
                    l['Reverse'] = True
                    if noProtDB:
                        l['Locus'] = int(l['Locus'][8:])
                    else:
                        l['Locus'] = l['Locus'][8:]
                else:
                    l['Reverse'] = False
                    if noProtDB:
                        l['Locus'] = int(l['Locus'])
                    else:
                        l['Locus'] = l['Locus']
            # Are all loci for a protein reverse?
            ## - shouldn't this logic be changed to: 'are any loci reverse?' and if so, set 'Reverse' to True?
            ## (because then we can't distinguish this peptide match from a fictional protein from a real protein)
            ## - There aren't typically many overlapping peptides between forward and reverse proteins anyway (~1%)
            if all([l['Reverse'] for x in protein['loci']]):
                protein['Reverse'] = True
            else:
                protein['Reverse'] = False
                
            # Pull out peptide sequences
            for p in protein['peptides']:
                p['AA_Sequence'] = re.findall('\.(.*)\.', p['Sequence'])[0]

                # MudPIT salt step (chromatography method from Xcalibur)
                '''To work with these
                05282015_lysed_AW_0518_Phe3_4.1364.1364.2
                05282015_lysed_AW_0518_Phe3_4_150529142251.1364.1364.2
                '''
                try:
                    lcstep = int(p['FileName'].split('.')[0].split('_')[-1])
                    if lcstep > 100:
                        lcstep = int(p['FileName'].split('.')[0].split('_')[-2])
                    p['LCStep'] = lcstep
                except ValueError:
                    p['LCStep'] = None
                
                # Scan number from instrument (unique per salt step) - from MS2 / SQT file
                p['Scan'] = int(p['FileName'].split('.')[1])

                # predicted ion charge from instrument - from MS2 / SQT file
                p['ChargeState'] = int(p['FileName'].split('.')[3])
            
            #protein['peptide_seq'] = set((x['AA_Sequence'] for x in protein['peptides']))
            protein['peptide_seq'] = list(set((x['AA_Sequence'] for x in protein['peptides'])))

            protein['forward_loci'] = [l['Locus'] for l in protein['loci'] if not l['Reverse']]
            protein['all_loci'] = [l['Locus'] for l in protein['loci']]
            if get_forward_loci:
                # Don't trust that blazmass has included all possible loci
                # Get list of protDB IDs for each peptide. Get intersection of IDs 
                # (list of IDs that are in all peptides)
                # -------
                # Not entirely accurate because this set of peptides along with another peptide may be present in another locus
                # explaining why a certain "possible" locus does not show up here. It should show up somewhere else
                # -------
                nr_result = list(seqDB.find({'_id':{'$in': list(protein['peptide_seq'])}}))
                # "if 'd' not in x" removes reverse IDs
                new_forward_loci = list(set.intersection(*[set([x['i'] for x in p['p'] if 'd' not in x]) for p in nr_result]))
                if set(new_forward_loci) != set(protein['forward_loci']):
                    print('Missing proteins in loci containing: ' + str(protein['all_loci'][0])) #printing from all_loci because forward may be empty
                    pass
                    
                protein['forward_loci'] = new_forward_loci
            
            if get_tax:
                # get all possible taxIDs
                taxIDs_result = taxDB.aggregate([{'$match':{'_id':{'$in':protein['forward_loci']}}},
                                  {'$group': {'_id': None, 'taxID': {'$addToSet': '$taxID'}}}])['result']
                if not taxIDs_result:
                    protein['LCA'] = None
                    continue
                taxIDs = taxIDs_result[0]['taxID']
                if taxIDs:
                    protein['LCA'] = t.LCA(taxIDs)
                    protein['taxIDs'] = taxIDs
                else:
                    protein['LCA'] = None
            
            if check_peptides:
                # Are all peptides found within the fasta sequences for all possible forward_loci ?
                # Skip reverse loci. May want to change this to use all loci, regardless of forward or reverse
                # to avoid some proteins not having these entries.
                # Keeping like this for now to keep compatibility with get_forward_loci lookup
                if protein['forward_loci']:
                    protein['protDB'] = list(protDB.find({'_id':{'$in': protein['forward_loci']}}))
                    defline, seq = zip(*[(x['d'],x['s']) for x in protein['protDB']])
                    protein['all_peptides_in_proteins'] = all([all([p in s for p in protein['peptide_seq']]) for s in seq])
                    if not protein['all_peptides_in_proteins']:
                        print('not all peptides in proteins' + str(protein['forward_loci'][0]))

            if get_hashes:
                protein['hashes'] = [x['_id'] for x in redunDB.find({'pID':{'$in': protein['forward_loci']}})]
                            
            if small:
                protein.pop('loci')
                protein.pop('peptides')
            
            if not return_reverse and protein['Reverse']: #skip this one if we are skipping reverse loci
                continue
                
            yield protein
