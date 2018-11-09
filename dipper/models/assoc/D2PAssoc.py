from dipper.models.assoc.Association import Assoc

__author__ = 'nlw'


class D2PAssoc(Assoc):
    """
    A specific association class for defining Disease-to-Phenotype
    relationships
    This assumes that a graph is created outside of this class,
    and nodes get added.
    By default, an association will assume the "has_phenotype" relationship,
    unless otherwise specified.

    """

    def __init__(
            self, graph, definedby, disease_id, phenotype_id,
            onset=None,
            frequency=None,
            rel=None
    ):
        super().__init__(graph, definedby)

        if rel is None:  # default
            rel = self.globaltt['has phenotype']
        # elif rel == self.globaltt[['has disposition']:  # lacks onset & freq

        self.onset = onset
        self.frequency = frequency

        self.disease_id = disease_id
        self.phenotype_id = phenotype_id

        self.set_subject(disease_id)
        self.set_relationship(rel)
        self.set_object(phenotype_id)

        return

    def set_association_id(self, assoc_id=None):

        if assoc_id is None:
            self.assoc_id = self.make_d2p_id()
        else:
            self.assoc_id = assoc_id

        return

    def add_association_to_graph(self):
        """
        The reified relationship between a disease and a phenotype is decorated
        with some provenance information.
        This makes the assumption that both the disease and phenotype
        are classes.

        :param g:

        :return:

        """

        # add the basic association nodes
        # if rel == self.globaltt[['has disposition']:

        Assoc.add_association_to_graph(self)

        object_is_literal = True

        if self.frequency is not None and self.frequency != '':
            self.graph.addTriple(
                self.assoc_id, self.globaltt['frequency'], self.frequency,
                object_is_literal)
        if self.onset is not None and self.onset != '':
            self.graph.addTriple(
                self.assoc_id, self.globaltt['onset'], self.onset, object_is_literal)

        return

    def make_d2p_id(self):
        """
        Make an association id for phenotypic associations with disease
        that is defined by:
        source of association + disease + relationship + phenotype
        + onset + frequency

        :return:

        """

        attributes = [self.onset, self.frequency]
        assoc_id = self.make_association_id(
            self.definedby, self.disease_id, self.rel, self.phenotype_id, attributes)

        return assoc_id
