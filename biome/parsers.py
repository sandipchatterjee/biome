#!/usr/bin/env python3

import re
from itertools import chain

def dtaselect_json(in_file, small=False, get_tax=False, check_peptides=False, get_hashes=False, return_reverse=True):
    """ steps through and parses a DTASelect-filter.txt file (generator function)
    :param in_file: path to DTASelect-filter.txt file
    :param small: get rid of keys: 'loci' and 'peptides'
    :param get_tax: Look up taxonomy information for each protDB ID
    :param check_peptides: Check if all peptide sequences are in all proteins sequences in 'forward_loci'
    :param get_hashes:
    :param return_reverse: include reverse loci
    :type in_file: str

        get_forward_loci is removed
        noProtDB is removed. If the locus contains a "||", the part before the pipes is determined to be the protID

    protein is a dict with (possible) fields:
        loci: list of locus dicts. described below
        peptides: list of peptide dicts. described below
        reverse: boolean. True if all loci for a protein are reverse
        peptide_seq: set. All peptide amino acid sequences
        forward_loci: list. 'Locus' fields in loci for forward loci
        all_loci: list. 'Locus' fields in loci
        name: string. The "representative" locus (the largest one by AA length)
        tax_id: list. Unique list of taxonomy IDs for all forward loci
        lca: Int or None. Lowest common ancestor of tax_ids
        hashes: list. MD5sums of protein sequences for forward_loci. len(hashes) gives the number of unique proteins matching

    loci: dict parsed from Loci lines in file. Mostly unchanged
        fields from file: Locus, Sequence Count, Spectrum Count, Sequence Coverage, Length, MolWt, pI, Validation Status, NSAF, EMPAI, Descriptive Name
        fields added:
            reverse: boolean. True if `locus` starts with "Reverse_"
            description: part after'||', if exists
    peptides: dict parsed from peptide lines in file. Mostly unchanged.
        fields from file: Unique, FileName, XCorr, DeltCN, Conf%, M+H+m CalcM+H+, TotalIntensity, SpR, SpScore, IonProportion, Redundancy, Sequence
        fields added:
            aa_sequence: `Sequence` with the left and right sequence stripped
            is_modified: boolean. True if the peptide has PTMs
            unmod_peptide: peptide sequence without PTMs
            diff_mass: mass difference of PTMs
            mods: list of tuples: (AA (amino acid that is modified), pos (1-based position within peptide), mass (mass of this PTM))
            lc_step, scan, charge_state:  parsed from `FileName`

    """

    def per_to_float(x):
        # '50%' -> 0.50
        return float(x[:-1]) / 100

    if get_tax:
        from ..analysis import taxonomy
        from pymongo import MongoClient
        client = MongoClient('wl-cmadmin', 27017)
        taxDB = client.taxDB.taxDB
        t = taxonomy.Taxonomy()

    if check_peptides:
        protDB = MongoClient('wl-cmadmin', 27018).ProtDB_072114.ProtDB_072114

    if get_hashes:
        client = MongoClient('wl-cmadmin', 27017)
        redunDB = client.redunDB.redunDB

    with open(in_file) as f:
        line = next(f)

        # Skip header.
        # TODO: parse it
        while not line.startswith('Locus'):
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
            while not line.startswith('\t') and not line.startswith('*'):  # While it starts with a number or "Rev'
                try:
                    loci.append(dict(zip(locus_columns, [x(y) for x, y in zip(locus_types, line.strip().split('\t'))])))
                except:
                    print("parsing line failed: " + line)
                line = next(f)

            # Read peptides
            peptides = []
            while line[0] in ['\t', '*'] and line != '\tProteins\tPeptide IDs\tSpectra\n':
                peptides.append(
                    dict(zip(peptide_columns, [x(y) for x, y in zip(peptide_types, line.rstrip().split('\t'))])))
                line = next(f)

            protein['peptides'] = peptides
            protein['loci'] = loci

            # Parse out reverse loci
            for l in protein['loci']:
                if l['Locus'].startswith('Reverse_'):
                    l['reverse'] = True
                    l['Locus'] = l['Locus'][8:]
                else:
                    l['reverse'] = False
                if l['Locus'].count("||"):
                    locus_split = l['Locus'].split('||')
                    l['description'] = '||'.join(locus_split[1:])
                    l['Locus'] = int(locus_split[0])
                else:
                    l['description'] = l['Locus']
                    l['Locus'] = int(l['Locus'])

            # Are all loci for a protein reverse?
            ## - shouldn't this logic be changed to: 'are any loci reverse?' and if so, set 'Reverse' to True?
            ## (because then we can't distinguish this peptide match from a fictional protein from a real protein)
            ## - There aren't typically many overlapping peptides between forward and reverse proteins anyway (~1%)
            if all([l['reverse'] for x in protein['loci']]):
                protein['reverse'] = True
            else:
                protein['reverse'] = False

            if not return_reverse and protein['reverse']:  # skip this one if we are skipping reverse loci
                continue

            # Pull out peptide sequences
            for p in protein['peptides']:
                p['aa_sequence'] = re.findall('\.(.*)\.', p['Sequence'])[0]
                p['is_modified'] = True if ')' in p['aa_sequence'] else False
                if p['is_modified']:
                    unmod_peptide = p['aa_sequence']
                    diff_mass = 0
                    mods = []
                    for match in re.finditer('\((.*?)\)', p['aa_sequence']):
                        mass = float(match.groups()[0])
                        AA = p['aa_sequence'][match.span()[0] - 1]
                        diff_mass += mass
                        pos = unmod_peptide.index(match.group())  # 1-based
                        mods.append((AA, pos, mass))
                        unmod_peptide = unmod_peptide.replace(match.group(), '', 1)
                    p['unmod_peptide'] = unmod_peptide
                    p['diff_mass'] = diff_mass
                    p['mods'] = mods

                # MudPIT salt step (chromatography method from Xcalibur)
                '''To work with these
                05282015_lysed_AW_0518_Phe3_4.1364.1364.2
                05282015_lysed_AW_0518_Phe3_4_150529142251.1364.1364.2
                '''
                try:
                    lcstep = int(p['FileName'].split('.')[0].split('_')[-1])
                    if lcstep > 100:
                        lcstep = int(p['FileName'].split('.')[0].split('_')[-2])
                    p['lc_step'] = lcstep
                except ValueError:
                    p['lc_step'] = None

                # Scan number from instrument (unique per salt step) - from MS2 / SQT file
                p['scan'] = int(p['FileName'].split('.')[1])

                # predicted ion charge from instrument - from MS2 / SQT file
                p['charge_state'] = int(p['FileName'].split('.')[3])

                # To try to not break things
                p['LCStep'] = p['lc_step']
                p['Scan'] = p['scan']
                p['ChargeState'] = p['charge_state']
                p['AA_Sequence'] = p['aa_sequence']
                p['isModified'] = p['is_modified']

            protein['peptide_seq'] = list(set((x['aa_sequence'] for x in protein['peptides'])))
            protein['forward_loci'] = [l['Locus'] for l in protein['loci'] if not l['reverse']]
            protein['all_loci'] = [l['Locus'] for l in protein['loci']]

            # get a "representative" locus (the largest one)
            max_length = max(l['Length'] for l in protein['loci'])
            protein['name'] = [l['description'] for l in protein['loci'] if l['Length'] == max_length][0]

            if get_tax:
                # get all possible taxIDs
                protDB_ids = [int(x.split('||')[0]) for x in protein['forward_loci']]
                taxIDs_doc = list(taxDB.aggregate(
                    [{'$match': {'_id': {'$in': protDB_ids}}},
                     {'$group': {'_id': None, 'taxID': {'$addToSet': '$taxID'}}}]))
                if taxIDs_doc:
                    protein['tax_id'] = taxIDs_doc[0]['taxID']
                    protein['lca'] = t.LCA(taxIDs_doc[0]['taxID'])
                else:
                    protein['tax_id'] = []
                    protein['lca'] = None
                # To try to not break things
                protein['LCA'] = protein['lca']

            if check_peptides:
                # Are all peptides found within the fasta sequences for all possible forward_loci ?
                # Skip reverse loci. May want to change this to use all loci, regardless of forward or reverse
                # to avoid some proteins not having these entries.
                # Keeping like this for now to keep compatibility with get_forward_loci lookup
                if protein['forward_loci']:
                    protein['protDB'] = list(protDB.find({'_id': {'$in': protein['forward_loci']}}))
                    defline, seq = zip(*[(x['d'], x['s']) for x in protein['protDB']])
                    protein['all_peptides_in_proteins'] = all(
                        [all([p in s for p in protein['peptide_seq']]) for s in seq])
                    if not protein['all_peptides_in_proteins']:
                        print('not all peptides in proteins' + str(protein['forward_loci'][0]))

            if get_hashes:
                protein['hashes'] = [x['_id'] for x in redunDB.find({'pID': {'$in': protein['forward_loci']}})]

            if small:
                del protein['loci']
                del protein['peptides']

            yield protein
