import csv
import logging
import re
import gzip

from dipper.sources.Source import Source
from dipper.models.Model import Model
from dipper.models.assoc.G2PAssoc import G2PAssoc
from dipper.models.Genotype import Genotype
from dipper.models.Reference import Reference
from dipper.models.GenomicFeature import Feature, makeChromID

#       https://www.animalgenome.org/tmp/QTL_EquCab2.0.gff.txt.gz'
# mapDwnLd36738TDWS.txt.gz   
AQDL = 'https://www.animalgenome.org/QTLdb'
LOG = logging.getLogger(__name__)


class AnimalQTLdb(Source):
    """
    The Animal Quantitative Trait Loci (QTL) database (Animal QTLdb)
    is designed to house publicly all available QTL and
    single-nucleotide polymorphism/gene association data on livestock
    animal species.  This includes:
        * chicken
        * horse
        * cow
        * sheep
        * rainbow trout
        * pig
    While most of the phenotypes here are related to animal husbandry,
    production, and rearing, integration of these phenotypes with other species
    may lead to insight for human disease.

    Here, we use the QTL genetic maps and their computed genomic locations to
    create associations between the QTLs and their traits.  The traits come in
    their internal Animal Trait ontology vocabulary, which they further map to
    [Vertebrate Trait](http://bioportal.bioontology.org/ontologies/VT),
    Product Trait, and Clinical Measurement Ontology vocabularies.

    Since these are only associations to broad locations,
    we link the traits via "is_marker_for", since there is no specific
    causative nature in the association.  p-values for the associations
    are attached to the Association objects.  We default to the UCSC build for
    the genomic coordinates, and make equivalences.

    Any genetic position ranges that are <0, we do not include here.

    """

    GENEINFO = 'ftp://ftp.ncbi.nih.gov/gene/DATA/GENE_INFO'
    GITDIP = 'https://raw.githubusercontent.com/monarch-initiative/dipper/master'

    files = {
        # defaulting to this
        'cattle_bp': {
            'file': 'QTL_Btau_4.6.gff.txt.gz',
            'url': AQDL + '/tmp/QTL_Btau_4.6.gff.txt.gz'},
        # disabling this for now
        # 'cattle_umd_bp': {
        #   'file': 'QTL_UMD_3.1.gff.txt.gz',
        #   'url': AQDL + '/tmp/QTL_UMD_3.1.gff.txt.gz'},
        'cattle_cm': {
            'file': 'cattle_QTLdata.txt',
            'url': AQDL + '/export/KSUI8GFHOT6/cattle_QTLdata.txt'},
        'chicken_bp': {
            'file': 'QTL_GG_4.0.gff.txt.gz',
            'url': AQDL + '/tmp/QTL_GG_4.0.gff.txt.gz'},
        'chicken_cm': {
            'file': 'chicken_QTLdata.txt',
            'url': AQDL + '/export/KSUI8GFHOT6/chicken_QTLdata.txt'},
        'pig_bp': {
            'file': 'QTL_SS_10.2.gff.txt.gz',
            'url': AQDL + '/tmp/QTL_SS_10.2.gff.txt.gz'},
        'pig_cm': {
            'file': 'pig_QTLdata.txt',
            'url': AQDL + '/export/KSUI8GFHOT6/pig_QTLdata.txt'},
        'sheep_bp': {
            'file': 'QTL_OAR_3.1.gff.txt.gz',
            'url': AQDL + '/tmp/QTL_OAR_3.1.gff.txt.gz'},
        'sheep_cm': {
            'file': 'sheep_QTLdata.txt',
            'url': AQDL + '/export/KSUI8GFHOT6/sheep_QTLdata.txt'},
        'horse_bp': {
            'file': 'QTL_EquCab2.0.gff.txt.gz',
            'url': AQDL + '/tmp/QTL_EquCab2.0.gff.txt.gz'},
        'horse_cm': {
            'file': 'horse_QTLdata.txt',
            'url': AQDL + '/export/KSUI8GFHOT6/horse_QTLdata.txt'},
        'rainbow_trout_cm': {
            'file': 'rainbow_trout_QTLdata.txt',
            'url': AQDL + '/export/KSUI8GFHOT6/rainbow_trout_QTLdata.txt'},

        #                  Gene_info from NCBI
        # to reasure TEC that when we see an integer
        # it is a gene identifier from NCBI for the species
        # misses will not block, but they will squawk, (the last three are homemade)

        # pig  # "Sus scrofa"  # NCBITaxon:9823
        'Sus_scrofa_info': {
            'file': 'Sus_scrofa.gene_info.gz',
            'url': GENEINFO + '/Mammalia/Sus_scrofa.gene_info.gz',
        },
        # cattle  # "Bos taurus"      # NCBITaxon:9913
        'Bos_taurus_info': {
            'file': 'Bos_taurus.gene_info.gz',
            'url': GENEINFO + '/Mammalia/Bos_taurus.gene_info.gz',
        },
        # chicken  # "Gallus gallus"  # NCBITaxon:9031
        'Gallus_gallus_info': {
            'file': 'Gallus_gallus.gene_info.gz',
            'url': GENEINFO + '/Non-mammalian_vertebrates/Gallus_gallus.gene_info.gz',
        },
        # horse  # "Equus caballus"  # NCBITaxon:9796
        'Equus_caballus_info': {
            'file': 'Equus_caballus.gene_info.gz',
            'url': GITDIP + '/resources/animalqtldb/Equus_caballus.gene_info.gz',
        },
        # sheep  # "Ovis aries"  # NCBITaxon:9940
        'Ovis_aries_info': {
            'file': 'Ovis_aries.gene_info.gz',
            'url': GITDIP + '/resources/animalqtldb/Ovis_aries.gene_info.gz',
        },
        # rainbow trout  # "Oncorhynchus mykiss"  # NCBITaxon:8022
        'Oncorhynchus_mykiss_info': {
            'file': 'Oncorhynchus_mykiss.gene_info.gz',
            'url': GITDIP + '/resources/animalqtldb/Oncorhynchus_mykiss.gene_info.gz',
        },
        ########################################
        # TODO add rainbow_trout_bp when available
        'trait_mappings': {
            'file': 'trait_mappings',
            'url': AQDL + '/export/trait_mappings.csv'
        },
    }

    # AQTL ids
    test_ids = {
        28483, 29016, 29018, 8945, 29385, 12532, 31023, 14234, 17138, 1795, 1798, 32133
    }

    def __init__(self, graph_type, are_bnodes_skolemized):
        super().__init__(
            graph_type,
            are_bnodes_skolemized,
            'animalqtldb',
            ingest_title='Animal QTL db',
            ingest_url='http://www.animalgenome.org/cgi-bin/QTLdb/index',
            license_url=None,
            data_rights="'" + AQDL + '/faq#32',
            # file_handle=None
        )

        self.gene_info = list()
        return

    def fetch(self, is_dl_forced=False):
        self.get_files(is_dl_forced)

        return

    def parse(self, limit=None):
        """

        :param limit:
        :return:
        """
        if limit is not None:
            LOG.info("Only parsing first %s rows fo each file", str(limit))

        LOG.info("Parsing files...")

        if self.test_only:
            self.test_mode = True
            graph = self.testgraph
        else:
            graph = self.graph

        traitmap = '/'.join((self.rawdir, self.files['trait_mappings']['file']))
        self._process_trait_mappings(traitmap, limit)

        geno = Genotype(graph)
        animals = ['chicken', 'pig', 'horse', 'rainbow_trout', 'sheep', 'cattle']

        for common_name in animals:
            txid_num = self.resolve(common_name).split(':')[1]
            taxon_label = self.localtt[common_name]
            taxon_curie = self.globaltt[taxon_label]
            taxon_num = taxon_curie.split(':')[1]
            txid_num = taxon_num  # for now
            taxon_word = taxon_label.replace(' ', '_')
            gene_info_file = '/'.join(
                (self.rawdir, self.files[taxon_word + '_info']['file']))
            self.gene_info = list()
            with gzip.open(gene_info_file, 'rt') as gi_gz:
                filereader = csv.reader(gi_gz, delimiter='\t')
                for row in filereader:
                    if row[0][0] == '#':
                        continue
                    else:
                        self.gene_info.append(str(row[1]))  # tossing lots of good stuff
            LOG.info(
                'Gene Info for %s has %i enteries', common_name, len(self.gene_info))
            # LOG.info('Gene Info entery looks like %s', self.gene_info[5])

            build = None

            fname_bp = common_name + '_bp'
            if fname_bp in self.files:
                bpfile = self.files[fname_bp]['file']
                mch = re.search(r'QTL_([\w\.]+)\.gff.txt.gz', bpfile)
                if mch is None:
                    LOG.error("Can't match a gff build to " + fname_bp)
                else:
                    build = mch.group(1)
                    build_id = self.localtt[build]
                    LOG.info("Build = %s", build_id)
                    geno.addReferenceGenome(build_id, build, txid_num)
                if build_id is not None:
                    self._process_qtls_genomic_location(
                        '/'.join((self.rawdir, bpfile)), txid_num, build_id, build,
                        common_name, limit)

            fname_cm = common_name + '_cm'
            if fname_cm in self.files:
                cmfile = self.files[fname_cm]['file']
                self._process_qtls_genetic_location(
                    '/'.join((self.rawdir, cmfile)), txid_num, common_name, limit)

        LOG.info("Finished parsing")
        return

    def _process_qtls_genetic_location(
            self, raw, txid, common_name, limit=None):
        """
        This function processes

        Triples created:

        :param limit:
        :return:

        """
        if self.test_mode:
            graph = self.testgraph
        else:
            graph = self.graph
        line_counter = 0
        geno = Genotype(graph)
        model = Model(graph)
        eco_id = self.globaltt['quantitative trait analysis evidence']

        taxon_curie = 'NCBITaxon:' + txid

        LOG.info("Processing genetic location for %s from %s", taxon_curie, raw)
        with open(raw, 'r', encoding="iso-8859-1") as csvfile:
            filereader = csv.reader(csvfile, delimiter='\t', quotechar='\"')
            for row in filereader:
                line_counter += 1
                (qtl_id,
                 qtl_symbol,
                 trait_name,
                 assotype,
                 empty,
                 chromosome,
                 position_cm,
                 range_cm,
                 flankmark_a2,
                 flankmark_a1,
                 peak_mark,
                 flankmark_b1,
                 flankmark_b2,
                 exp_id,
                 model_id,
                 test_base,
                 sig_level,
                 lod_score,
                 ls_mean,
                 p_values,
                 f_statistics,
                 variance,
                 bayes_value,
                 likelihood_ratio,
                 trait_id, dom_effect,
                 add_effect,
                 pubmed_id,
                 gene_id,
                 gene_id_src,
                 gene_id_type,
                 empty2) = row

                if self.test_mode and int(qtl_id) not in self.test_ids:
                    continue

                qtl_id = common_name + 'QTL:' + qtl_id.strip()
                trait_id = 'AQTLTrait:' + trait_id.strip()

                # Add QTL to graph
                feature = Feature(graph, qtl_id, qtl_symbol, self.globaltt['QTL'])
                feature.addTaxonToFeature(taxon_curie)

                # deal with the chromosome
                chrom_id = makeChromID(chromosome, taxon_curie, 'CHR')

                # add a version of the chromosome which is defined as
                # the genetic map
                build_id = 'MONARCH:'+common_name.strip()+'-linkage'
                build_label = common_name+' genetic map'
                geno.addReferenceGenome(build_id, build_label, taxon_curie)
                chrom_in_build_id = makeChromID(chromosome, build_id, 'MONARCH')
                geno.addChromosomeInstance(
                    chromosome, build_id, build_label, chrom_id)
                start = stop = None
                # range_cm sometimes ends in "(Mb)"  (i.e pig 2016 Nov)
                range_mb = re.split(r'\(', range_cm)
                if range_mb is not None:
                    range_cm = range_mb[0]

                if re.search(r'[0-9].*-.*[0-9]', range_cm):
                    range_parts = re.split(r'-', range_cm)

                    # check for poorly formed ranges
                    if len(range_parts) == 2 and\
                            range_parts[0] != '' and range_parts[1] != '':
                        (start, stop) = [
                            int(float(x.strip())) for x in re.split(r'-', range_cm)]
                    else:
                        LOG.info(
                            "A cM range we can't handle for QTL %s: %s",
                            qtl_id, range_cm)
                elif position_cm != '':
                    match = re.match(r'([0-9]*\.[0-9]*)', position_cm)
                    if match is not None:
                        position_cm = match.group()
                        start = stop = int(float(position_cm))

                # FIXME remove converion to int for start/stop
                # when schema can handle floats add in the genetic location
                # based on the range
                feature.addFeatureStartLocation(
                    start, chrom_in_build_id, None,
                    [self.globaltt['FuzzyPosition']])
                feature.addFeatureEndLocation(
                    stop, chrom_in_build_id, None,
                    [self.globaltt['FuzzyPosition']])
                feature.addFeatureToGraph()

                # sometimes there's a peak marker, like a rsid.
                # we want to add that as a variant of the gene,
                # and xref it to the qtl.
                dbsnp_id = None
                if peak_mark != '' and peak_mark != '.' and \
                        re.match(r'rs', peak_mark.strip()):
                    dbsnp_id = 'dbSNP:'+peak_mark.strip()

                    model.addIndividualToGraph(
                        dbsnp_id, None,
                        self.globaltt['sequence_alteration'])
                    model.addXref(qtl_id, dbsnp_id)

                gene_id = gene_id.replace('uncharacterized ', '').strip()
                if gene_id is not None and gene_id != '' and gene_id != '.'\
                        and re.fullmatch(r'[^ ]*', gene_id) is not None:

                    # we assume if no src is provided and gene_id is an integer,
                    # then it is an NCBI gene ... (okay, lets crank that back a notch)
                    if gene_id_src == '' and gene_id.isdigit() and \
                            gene_id in self.gene_info:
                        # LOG.info(
                        #    'Warm & Fuzzy saying %s is a NCBI gene for %s',
                        #    gene_id, common_name)
                        gene_id_src = 'NCBIgene'
                    elif gene_id_src == '' and gene_id.isdigit():
                        LOG.warning(
                            'Cold & Prickely saying %s is a NCBI gene for %s',
                            gene_id, common_name)
                        gene_id_src = 'NCBIgene'
                    elif gene_id_src == '':
                        LOG.error(
                            ' "%s" is a NOT NCBI gene for %s', gene_id, common_name)
                        gene_id_src = None

                    if gene_id_src == 'NCBIgene':
                        gene_id = 'NCBIGene:' + gene_id
                        # we will expect that these will get labels elsewhere
                        geno.addGene(gene_id, None)
                        # FIXME what is the right relationship here?
                        geno.addAffectedLocus(qtl_id, gene_id)

                        if dbsnp_id is not None:
                            # add the rsid as a seq alt of the gene_id
                            vl_id = '_:' + re.sub(
                                r':', '', gene_id) + '-' + peak_mark.strip()
                            geno.addSequenceAlterationToVariantLocus(
                                dbsnp_id, vl_id)
                            geno.addAffectedLocus(vl_id, gene_id)

                # add the trait
                model.addClassToGraph(trait_id, trait_name)

                # Add publication
                reference = None
                if re.match(r'ISU.*', pubmed_id):
                    pub_id = 'AQTLPub:'+pubmed_id.strip()
                    reference = Reference(graph, pub_id)
                elif pubmed_id != '':
                    pub_id = 'PMID:' + pubmed_id.strip()
                    reference = Reference(
                        graph, pub_id, self.globaltt['journal article'])

                if reference is not None:
                    reference.addRefToGraph()

                # make the association to the QTL
                assoc = G2PAssoc(
                    graph, self.name, qtl_id, trait_id, self.globaltt['is marker for'])
                assoc.add_evidence(eco_id)
                assoc.add_source(pub_id)

                # create a description from the contents of the file
                # desc = ''

                # assoc.addDescription(g, assoc_id, desc)

                # TODO add exp_id as evidence
                # if exp_id != '':
                #     exp_id = 'AQTLExp:'+exp_id
                #     gu.addIndividualToGraph(g, exp_id, None, eco_id)

                if p_values != '':
                    scr = re.sub(r'<', '', p_values)
                    scr = re.sub(r',', '.', scr)  # international notation
                    if scr.isnumeric():
                        score = float(scr)
                        assoc.set_score(score)  # todo add score type
                # TODO add LOD score?
                assoc.add_association_to_graph()

                # make the association to the dbsnp_id, if found
                if dbsnp_id is not None:
                    # make the association to the dbsnp_id
                    assoc = G2PAssoc(
                        graph, self.name, dbsnp_id, trait_id,
                        self.globaltt['is marker for'])
                    assoc.add_evidence(eco_id)
                    assoc.add_source(pub_id)

                    # create a description from the contents of the file
                    # desc = ''
                    # assoc.addDescription(g, assoc_id, desc)

                    # TODO add exp_id
                    # if exp_id != '':
                    #     exp_id = 'AQTLExp:'+exp_id
                    #     gu.addIndividualToGraph(g, exp_id, None, eco_id)

                    if p_values != '':
                        scr = re.sub(r'<', '', p_values)
                        scr = re.sub(r',', '.', scr)
                        if scr.isnumeric():
                            score = float(scr)
                            assoc.set_score(score)  # todo add score type
                    # TODO add LOD score?

                    assoc.add_association_to_graph()

                if not self.test_mode and limit is not None and line_counter > limit:
                    break

        LOG.info("Done with QTL genetic info")
        return

    def _process_qtls_genomic_location(
            self, raw, txid, build_id, build_label, common_name, limit=None):
        """
        This method

        Triples created:

        :param limit:
        :return:
        """
        if self.test_mode:
            graph = self.testgraph
        else:
            graph = self.graph
        model = Model(graph)
        line_counter = 0
        geno = Genotype(graph)
        # assume that chrs get added to the genome elsewhere

        taxon_curie = 'NCBITaxon:' + txid
        eco_id = self.globaltt['quantitative trait analysis evidence']
        LOG.info("Processing QTL locations for %s from %s", taxon_curie, raw)
        with gzip.open(raw, 'rt', encoding='ISO-8859-1') as tsvfile:
            reader = csv.reader(tsvfile, delimiter="\t")
            for row in reader:
                line_counter += 1
                if re.match(r'^#', ' '.join(row)):
                    continue

                (chromosome, qtl_source, qtl_type, start_bp, stop_bp, frame, strand,
                 score, attr) = row
                example = '''
Chr.Z   Animal QTLdb    Production_QTL  33954873      34023581...
QTL_ID=2242;Name="Spleen percentage";Abbrev="SPLP";PUBMED_ID=17012160;trait_ID=2234;
trait="Spleen percentage";breed="leghorn";"FlankMarkers=ADL0022";VTO_name="spleen mass";
MO_name="spleen weight to body weight ratio";Map_Type="Linkage";Model="Mendelian";
Test_Base="Chromosome-wise";Significance="Significant";P-value="<0.05";F-Stat="5.52";
Variance="2.94";Dominance_Effect="-0.002";Additive_Effect="0.01
                '''
                str(example)
                # make dictionary of attributes
                # keys are:
                # QTL_ID,Name,Abbrev,PUBMED_ID,trait_ID,trait,FlankMarkers,
                # VTO_name,Map_Type,Significance,P-value,Model,
                # Test_Base,Variance, Bayes-value,PTO_name,gene_IDsrc,peak_cM,
                # CMO_name,gene_ID,F-Stat,LOD-score,Additive_Effect,
                # Dominance_Effect,Likelihood_Ratio,LS-means,Breed,
                # trait (duplicate with Name),Variance,Bayes-value,
                # F-Stat,LOD-score,Additive_Effect,Dominance_Effect,
                # Likelihood_Ratio,LS-means

                # deal with poorly formed attributes
                if re.search(r'"FlankMarkers";', attr):
                    attr = re.sub(r'FlankMarkers;', '', attr)
                attr_items = re.sub(r'"', '', attr).split(";")
                bad_attrs = set()
                for attributes in attr_items:
                    if not re.search(r'=', attributes):
                        # remove this attribute from the list
                        bad_attrs.add(attributes)

                attr_set = set(attr_items) - bad_attrs
                attribute_dict = dict(item.split("=") for item in attr_set)

                qtl_num = attribute_dict.get('QTL_ID')
                if self.test_mode and int(qtl_num) not in self.test_ids:
                    continue
                # make association between QTL and trait based on taxon

                qtl_id = common_name + 'QTL:' + str(qtl_num)
                model.addIndividualToGraph(qtl_id, None, self.globaltt['QTL'])
                geno.addTaxon(taxon_curie, qtl_id)

                trait_id = 'AQTLTrait:' + attribute_dict.get('trait_ID')

                # if pub is in attributes, add it to the association
                pub_id = None
                if 'PUBMED_ID' in attribute_dict.keys():
                    pub_id = attribute_dict.get('PUBMED_ID')
                    if re.match(r'ISU.*', pub_id):
                        pub_id = 'AQTLPub:' + pub_id.strip()
                        reference = Reference(graph, pub_id)
                    else:
                        pub_id = 'PMID:' + pub_id.strip()
                        reference = Reference(
                            graph, pub_id, self.globaltt['journal article'])
                    reference.addRefToGraph()

                # Add QTL to graph
                assoc = G2PAssoc(
                    graph, self.name, qtl_id, trait_id,
                    self.globaltt['is marker for'])
                assoc.add_evidence(eco_id)
                assoc.add_source(pub_id)
                if 'P-value' in attribute_dict.keys():
                    scr = re.sub(r'<', '', attribute_dict.get('P-value'))
                    if ',' in scr:
                        scr = re.sub(r',', '.', scr)
                    if scr.isnumeric():
                        score = float(scr)
                        assoc.set_score(score)

                assoc.add_association_to_graph()
                # TODO make association to breed
                # (which means making QTL feature in Breed background)

                # get location of QTL
                chromosome = re.sub(r'Chr\.', '', chromosome)
                chrom_id = makeChromID(chromosome, taxon_curie, 'CHR')

                chrom_in_build_id = makeChromID(chromosome, build_id, 'MONARCH')
                geno.addChromosomeInstance(
                    chromosome, build_id, build_label, chrom_id)
                qtl_feature = Feature(graph, qtl_id, None, self.globaltt['QTL'])
                if start_bp == '':
                    start_bp = None
                qtl_feature.addFeatureStartLocation(
                    start_bp, chrom_in_build_id, strand,
                    [self.globaltt['FuzzyPosition']])
                if stop_bp == '':
                    stop_bp = None
                qtl_feature.addFeatureEndLocation(
                    stop_bp, chrom_in_build_id, strand,
                    [self.globaltt['FuzzyPosition']])
                qtl_feature.addTaxonToFeature(taxon_curie)
                qtl_feature.addFeatureToGraph()

                if not self.test_mode and limit is not None and line_counter > limit:
                    break

        LOG.warning("Bad attribute flags in this file")
        LOG.info("Done with QTL genomic mappings for %s", taxon_curie)
        return

    def _process_trait_mappings(self, raw, limit=None):
        """
        This method mapps traits from/to ...

        Triples created:

        :param limit:
        :return:
        """
        if self.test_mode:
            graph = self.testgraph
        else:
            graph = self.graph
        line_counter = 0
        model = Model(graph)

        with open(raw, 'r') as csvfile:
            filereader = csv.reader(csvfile, delimiter=',', quotechar='\"')
            next(filereader, None)  # skip header line
            for row in filereader:
                line_counter += 1
                # need to skip the last line
                if len(row) < 8:
                    LOG.info("skipping line %d: %s", line_counter, '\t'.join(row))
                    continue
                (vto_id, pto_id, cmo_id, ato_column, species, trait_class,
                 trait_type, qtl_count) = row

                ato_id = re.sub(
                    r'ATO #', 'AQTLTrait:', re.sub(
                        r'\].*', '', re.sub(r'\[', '', ato_column)))
                ato_id = ato_id.strip()

                ato_label = re.sub(r'.*\]\s*', '', ato_column)

                model.addClassToGraph(ato_id, ato_label.strip())

                if re.match(r'VT:.*', vto_id):
                    model.addClassToGraph(vto_id, None)
                    model.addEquivalentClass(ato_id, vto_id)
                if re.match(r'LPT:.*', pto_id):
                    model.addClassToGraph(pto_id, None)
                    model.addXref(ato_id, pto_id)
                if re.match(r'CMO:.*', cmo_id):
                    model.addClassToGraph(cmo_id, None)
                    model.addXref(ato_id, cmo_id)

        LOG.info("Done with trait mappings")
        return

    def getTestSuite(self):
        import unittest
        from tests.test_animalqtl import AnimalQTLdbTestCase

        test_suite = unittest.TestLoader().loadTestsFromTestCase(AnimalQTLdbTestCase)

        return test_suite
