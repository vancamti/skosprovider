# -*- coding: utf-8 -*-

'''This module provides an abstraction of controlled vocabularies.

This abstraction allows our application to work with both local and remote
vocabs (be they SOAP, REST, XML-RPC or something else).

The basic idea is that we have skos providers. Each provider is an instance
of a :class:`VocabularyProvider`. The same class can thus be reused with
different configurations to handle different vocabs. Generally speaking, every
instance of a certain :class:`VocabularyProvider` will deal with concepts and
collections from a single conceptscheme.
'''

from __future__ import unicode_literals

import abc
import copy
import logging
from operator import methodcaller

from .skos import (
    Concept,
    Collection,
    ConceptScheme
)

from .uri import (
    DefaultUrnGenerator,
    DefaultConceptSchemeUrnGenerator
)

log = logging.getLogger(__name__)


class VocabularyProvider:
    '''An interface that all vocabulary providers must follow.
    '''

    __metaclass__ = abc.ABCMeta

    concept_scheme = None
    '''The :class:`~skosprovider.skos.ConceptScheme` this provider serves.'''

    uri_generator = None
    '''The :class:`~skosprovider.uri.UriGenerator` responsible for generating
    :term:`URIs <uri>` for this provider.'''

    def __init__(self, metadata, **kwargs):
        '''Create a new provider and register some metadata.


        :param uri_generator: An object that implements the
            :class:`skosprovider.uri.UriGenerator` interface.
        :param concept_scheme: A :class:`~skosprovider.skos.ConceptScheme`. If
            not present, a default :class:`~skosprovider.skos.ConceptScheme`
            will be created with a uri generated by the
            :class:`~skosprovider.uri.DefaultConceptSchemeUrnGenerator` in
            combination with the provider `id`.
        :param dict metadata: Metadata essential to this provider. Expected
            metadata:

                * `id`: A unique identifier for the vocabulary. Required.
                * `default_language`: Used to determine what language to use when \
                    returning labels if no language is specified. Will default \
                    to `en` if not specified.
                * `subject`: A list of subjects or tags that define what the \
                    provider is about or what the provider can handle. This \
                    information can then be used when querying a \
                    :class:`~skosprovider.registry.Registry` for providers.
        '''
        if 'subject' not in metadata:
            metadata['subject'] = []
        self.metadata = metadata
        if 'uri_generator' in kwargs:
            self.uri_generator = kwargs.get('uri_generator')
        else:
            self.uri_generator = DefaultUrnGenerator(self.metadata.get('id'))
        if 'concept_scheme' in kwargs:
            self.concept_scheme = kwargs.get('concept_scheme')
        else:
            self.concept_scheme = ConceptScheme(
                uri=DefaultConceptSchemeUrnGenerator().generate(
                    id=self.metadata.get('id')
                )
            )

    def _get_language(self, **kwargs):
        '''Determine what language to render labels in.

        Will first check if there's a language keyword specified in **kwargs.
        If not, will check the default language of the provider. If there's no
        default language, will fall back to 'en'.

        :rtype: str
        '''
        return kwargs.get(
            'language',
            self.metadata.get('default_language', 'en')
        )

    def _get_sort(self, **kwargs):
        '''Determine on what attribute to sort.

        :rtype: str
        '''
        return kwargs.get('sort', None)

    def _get_sort_order(self, **kwargs):
        '''Determine the sort order.

        :rtype: str
        :returns: 'asc' or 'desc'
        '''
        return kwargs.get('sort_order', 'asc')

    def _sort(self, concepts, sort=None, language='any', reverse=False):
        '''
        Returns a sorted version of a list of concepts. Will leave the original
        list unsorted.

        :param list concepts: A list of concepts and collections.
        :param string sort: What to sort on: `id`, `label` or `sortlabel`
        :param string language: Language to use when sorting on `label` or
            `sortlabel`.
        :param boolean reverse: Reverse the sort order?
        :rtype: list
        '''
        sorted = copy.copy(concepts)
        if sort:
            sorted.sort(key=methodcaller('_sortkey', sort, language), reverse=reverse)
        return sorted

    def get_vocabulary_id(self):
        '''Get an identifier for the vocabulary.

        :rtype: String or number.
        '''
        return self.metadata.get('id')

    def get_metadata(self):
        '''Get some metadata on the provider or the vocab it represents.

        :rtype: Dict.
        '''
        return self.metadata

    @abc.abstractmethod
    def get_by_id(self, id):
        '''Get all information on a concept or collection, based on id.

        Providers should assume that all id's passed are strings. If a provider
        knows that internally it uses numeric identifiers, it's up to the
        provider to do the typecasting. Generally, this should not be done by
        changing the id's themselves (eg. from int to str), but by doing the
        id comparisons in a type agnostic way.

        Since this method could be used to find both concepts and collections,
        it's assumed that there are no id collisions between concepts and
        collections.

        :rtype: :class:`skosprovider.skos.Concept` or
            :class:`skosprovider.skos.Collection` or `False` if the concept or
            collection is unknown to the provider.
        '''

    @abc.abstractmethod
    def get_by_uri(self, uri):
        '''Get all information on a concept or collection, based on a
        :term:`URI`.

        :rtype: :class:`skosprovider.skos.Concept` or
            :class:`skosprovider.skos.Collection` or `False` if the concept or
            collection is unknown to the provider.
        '''

    @abc.abstractmethod
    def get_all(self, **kwargs):
        '''Returns all concepts and collections in this provider.

        :param string language: Optional. If present, it should be a
            :term:`language-tag`. This language-tag is passed on to the
            underlying providers and used when selecting the label to display
            for each concept.
        :param string sort: Optional. If present, it should either be `id`,
            `label` or `sortlabel`. The `sortlabel` option means the providers should
            take into account any `sortLabel` if present, if not it will
            fallback to a regular label to sort on.
        :param string sort_order: Optional. What order to sort in: `asc` or
            `desc`. Defaults to `asc`

        :returns: A :class:`lst` of concepts and collections. Each of these is a dict
            with the following keys:

            * id: id within the conceptscheme
            * uri: :term:`uri` of the concept or collection
            * type: concept or collection
            * label: A label to represent the concept or collection. It is \
                determined by looking at the `language` parameter, the default \
                language of the provider and finally falls back to `en`.

        '''

    @abc.abstractmethod
    def get_top_concepts(self, **kwargs):
        '''
        Returns all top-level concepts in this provider.

        Top-level concepts are concepts that have no broader concepts
        themselves. They might have narrower concepts, but this is not
        mandatory.

        :param string language: Optional. If present, it should be a
            :term:`language-tag`. This language-tag is passed on to the
            underlying providers and used when selecting the label to display
            for each concept.
        :param string sort: Optional. If present, it should either be `id`,
            `label` or `sortlabel`. The `sortlabel` option means the providers should
            take into account any `sortLabel` if present, if not it will
            fallback to a regular label to sort on.
        :param string sort_order: Optional. What order to sort in: `asc` or
            `desc`. Defaults to `asc`

        :returns: A :class:`lst` of concepts, NOT collections. Each of these
            is a dict with the following keys:

            * id: id within the conceptscheme
            * uri: :term:`uri` of the concept or collection
            * type: concept or collection
            * label: A label to represent the concept or collection. It is \
                determined by looking at the `language` parameter, the default \
                language of the provider and finally falls back to `en`.

        '''

    @abc.abstractmethod
    def find(self, query, **kwargs):
        '''Find concepts that match a certain query.

        Currently query is expected to be a dict, so that complex queries can
        be passed. You can use this dict to search for concepts or collections
        with a certain label, with a certain type and for concepts that belong
        to a certain collection.

        .. code-block:: python

            # Find anything that has a label of church.
            provider.find({'label': 'church'})

            # Find all concepts that are a part of collection 5.
            provider.find({'type': 'concept', 'collection': {'id': 5})

            # Find all concepts, collections or children of these
            # that belong to collection 5.
            provider.find({'collection': {'id': 5, 'depth': 'all'})

            # Find anything that has a label of church.
            # Preferentially display a label in Dutch.
            provider.find({'label': 'church'}, language='nl')

        :param query: A dict that can be used to express a query. The following
            keys are permitted:

            * `label`: Search for something with this label value. An empty \
                label is equal to searching for all concepts.
            * `type`: Limit the search to certain SKOS elements. If not \
                present or `None`, `all` is assumed:

                * `concept`: Only return :class:`skosprovider.skos.Concept` \
                    instances.
                * `collection`: Only return \
                    :class:`skosprovider.skos.Collection` instances.
                * `all`: Return both :class:`skosprovider.skos.Concept` and \
                    :class:`skosprovider.skos.Collection` instances.
            * `collection`: Search only for concepts belonging to a certain \
                collection. This argument should be a dict with two keys:

                * `id`: The id of a collection. Required.
                * `depth`: Can be `members` or `all`. Optional. If not \
                    present, `members` is assumed, meaning only concepts or \
                    collections that are a direct member of the collection \
                    should be considered. When set to `all`, this method \
                    should return concepts and collections that are a member \
                    of the collection or are a narrower concept of a member \
                    of the collection.

        :param string language: Optional. If present, it should be a
            :term:`language-tag`. This language-tag is passed on to the
            underlying providers and used when selecting the label to display
            for each concept.
        :param string sort: Optional. If present, it should either be `id`,
            `label` or `sortlabel`. The `sortlabel` option means the providers should
            take into account any `sortLabel` if present, if not it will
            fallback to a regular label to sort on.
        :param string sort_order: Optional. What order to sort in: `asc` or
            `desc`. Defaults to `asc`

        :returns: A :class:`lst` of concepts and collections. Each of these
            is a dict with the following keys:

            * id: id within the conceptscheme
            * uri: :term:`uri` of the concept or collection
            * type: concept or collection
            * label: A label to represent the concept or collection. It is \
                determined by looking at the `language` parameter, the default \
                language of the provider and finally falls back to `en`.

        '''

    @abc.abstractmethod
    def expand(self, id):
        '''Expand a concept or collection to all it's narrower
        concepts.

        This method should recurse and also return narrower concepts
        of narrower concepts.

        If the id passed belongs to a :class:`skosprovider.skos.Concept`,
        the id of the concept itself should be include in the return value.

        If the id passed belongs to a :class:`skosprovider.skos.Collection`,
        the id of the collection itself must not be present in the return value
        In this case the return value includes all the member concepts and
        their narrower concepts.

        :param id: A concept or collection id.
        :rtype: A list of id's or `False` if the concept or collection doesn't
            exist.
        '''

    def get_top_display(self, **kwargs):
        '''
        Returns all concepts or collections that form the top-level of a
        display hierarchy.

        As opposed to the :meth:`get_top_concepts`, this method can possibly
        return both concepts and collections.

        :param string language: Optional. If present, it should be a
            :term:`language-tag`. This language-tag is passed on to the
            underlying providers and used when selecting the label to display
            for each concept.
        :param string sort: Optional. If present, it should either be `id`,
            `label` or `sortlabel`. The `sortlabel` option means the providers should
            take into account any `sortLabel` if present, if not it will
            fallback to a regular label to sort on.
        :param string sort_order: Optional. What order to sort in: `asc` or
            `desc`. Defaults to `asc`

        :returns: A :class:`lst` of concepts and collections. Each of these
            is a dict with the following keys:

            * id: id within the conceptscheme
            * uri: :term:`uri` of the concept or collection
            * type: concept or collection
            * label: A label to represent the concept or collection. It is\
                determined by looking at the `language` parameter, the default\
                language of the provider and finally falls back to `en`.

        '''

    def get_children_display(self, id, **kwargs):
        '''
        Return a list of concepts or collections that should be displayed
        under this concept or collection.

        :param string language: Optional. If present, it should be a
            :term:`language-tag`. This language-tag is passed on to the
            underlying providers and used when selecting the label to display
            for each concept.
        :param string sort: Optional. If present, it should either be `id`,
            `label` or `sortlabel`. The `sortlabel` option means the providers should
            take into account any `sortLabel` if present, if not it will
            fallback to a regular label to sort on.
        :param string sort_order: Optional. What order to sort in: `asc` or
            `desc`. Defaults to `asc`

        :param str id: A concept or collection id.
        :returns: A :class:`lst` of concepts and collections. Each of these
            is a dict with the following keys:

            * id: id within the conceptscheme
            * uri: :term:`uri` of the concept or collection
            * type: concept or collection
            * label: A label to represent the concept or collection. It is \
                determined by looking at the `language` parameter, the default \
                language of the provider and finally falls back to `en`.

        '''


class MemoryProvider(VocabularyProvider):
    '''
    A provider that keeps everything in memory.

    The data is passed in the constructor of this provider as a :class:`lst` of
    :class:`skosprovider.skos.Concept` and :class:`skosprovider.skos.Collection`
    instances.
    '''

    case_insensitive = True
    '''
    Is searching for labels case insensitive?

    By default a search for a label is done case insensitive. Older versions of
    this provider were case sensitive. If this behaviour is desired, this can
    be triggered by providing a `case_insensitive` keyword to the constructor.
    '''

    def __init__(self, metadata, list, **kwargs):
        '''
        :param dict metadata: A dictionary with keywords like language.
        :param list list: A list of :class:`skosprovider.skos.Concept` and
            :class:`skosprovider.skos.Collection` instances.
        :param Boolean case_insensitive: Should searching for labels be done
            case-insensitive?
        '''
        super(MemoryProvider, self).__init__(metadata, **kwargs)
        self.list = list
        if 'case_insensitive' in kwargs:
            self.case_insensitive = kwargs['case_insensitive']

    def get_by_id(self, id):
        id = str(id)
        for c in self.list:
            if str(c.id) == id:
                return c
        return False

    def get_by_uri(self, uri):
        uri = str(uri)
        for c in self.list:
            if str(c.uri) == uri:
                return c
        return False

    def find(self, query, **kwargs):
        query = self._normalise_query(query)
        filtered = [c for c in self.list if self._include_in_find(c, query)]
        language = self._get_language(**kwargs)
        sort = self._get_sort(**kwargs)
        sort_order = self._get_sort_order(**kwargs)
        return [self._get_find_dict(c, **kwargs) for c in self._sort(filtered, sort, language, sort_order == 'desc')]

    def _normalise_query(self, query):
        '''
        :param query: A dict that can be used to express a query.
        :rtype: dict
        '''
        if 'type' in query and query['type'] not in ['concept', 'collection']:
            del query['type']
        return query

    def _include_in_find(self, c, query):
        '''
        :param c: A :class:`skosprovider.skos.Concept` or
            :class:`skosprovider.skos.Collection`.
        :param query: A dict that can be used to express a query.
        :rtype: boolean
        '''
        include = True
        if include and 'type' in query:
            include = query['type'] == c.type
        if include and 'label' in query:
            def finder(l, query):
                if not self.case_insensitive:
                    return l.label.find(query['label'])
                else:
                    return l.label.upper().find(query['label'].upper())
            include = any([finder(l, query) >= 0 for l in c.labels])
        if include and 'collection' in query:
            coll = self.get_by_id(query['collection']['id'])
            if not coll or not isinstance(coll, Collection):
                raise ValueError(
                    'You are searching for items in an unexisting collection.'
                )
            if 'depth' in query['collection'] and query['collection']['depth'] == 'all':
                members = self.expand(coll.id)
            else:
                members = coll.members
            include = any([True for id in members if str(id) == str(c.id)]) 
        return include

    def _get_find_dict(self, c, **kwargs):
        '''
        Return a dict that can be used in the return list of the :meth:`find`
        method.

        :param c: A :class:`skosprovider.skos.Concept` or
            :class:`skosprovider.skos.Collection`.
        :rtype: dict
        '''
        language = self._get_language(**kwargs)
        return {
            'id': c.id,
            'uri': c.uri,
            'type': c.type,
            'label': None if c.label() is None else c.label(language).label
        }

    def get_all(self, **kwargs):
        language = self._get_language(**kwargs)
        sort = self._get_sort(**kwargs)
        sort_order = self._get_sort_order(**kwargs)
        return [self._get_find_dict(c, **kwargs) for c in self._sort(self.list, sort, language, sort_order == 'desc')]

    def get_top_concepts(self, **kwargs):
        language = self._get_language(**kwargs)
        sort = self._get_sort(**kwargs)
        sort_order = self._get_sort_order(**kwargs)
        tc = [c for c in self.list if isinstance(c, Concept) and len(c.broader) == 0]
        return [self._get_find_dict(c, **kwargs) for c in self._sort(tc, sort, language, sort_order == 'desc')]

    def expand(self, id):
        id = str(id)
        for c in self.list:
            if str(c.id) == id:
                if isinstance(c, Concept):
                    ret = set([c.id])
                    for cid in c.narrower:
                        ret |= set(self.expand(cid))
                    return list(ret)
                elif isinstance(c, Collection):
                    ret = set([])
                    for m in c.members:
                        ret |= set(self.expand(m))
                    return list(ret)
        return False

    def get_top_display(self, **kwargs):
        language = self._get_language(**kwargs)
        sort = self._get_sort(**kwargs)
        sort_order = self._get_sort_order(**kwargs)
        td = [c for c in self.list if
              (isinstance(c, Concept) and len(c.broader) == 0 and len(c.member_of) == 0) or
              (isinstance(c, Collection) and len(c.superordinates) == 0 and len(c.member_of) == 0)]
        return [
            {
                'id': c.id,
                'uri': c.uri,
                'type': c.type,
                'label': None if c.label() is None else c.label(language).label
            } for c in self._sort(td, sort, language, sort_order == 'desc')]

    def get_children_display(self, id, **kwargs):
        c = self.get_by_id(id)
        if not c:
            return False
        language = self._get_language(**kwargs)
        sort = self._get_sort(**kwargs)
        sort_order = self._get_sort_order(**kwargs)
        if isinstance(c, Concept):
            if len(c.subordinate_arrays) == 0:
                display_children = c.narrower
            else:
                display_children = c.subordinate_arrays
        else:
            display_children = c.members
        dc = [self.get_by_id(dcid) for dcid in display_children]
        return [
            {
                'id': co.id,
                'uri': co.uri,
                'type': co.type,
                'label': None if co.label() is None else co.label(language).label
            } for co in self._sort(dc, sort, language, sort_order == 'desc')]


class DictionaryProvider(MemoryProvider):
    '''A simple vocab provider that use a python list of dicts.

    The provider expects a list with elements that are dicts that represent
    the concepts.
    '''

    def __init__(self, metadata, list, **kwargs):
        super(DictionaryProvider, self).__init__(metadata, [], **kwargs)
        self.list = [self._from_dict(c) for c in list]

    def _from_dict(self, data):
        if 'type' in data and data['type'] == 'collection':
            return Collection(
                id=data['id'],
                uri=data.get('uri') if data.get('uri') is not None else self.uri_generator.generate(type='collection', id=data['id']),
                concept_scheme=self.concept_scheme,
                labels=data.get('labels', []),
                notes=data.get('notes', []),
                sources=data.get('sources', []),
                members=data.get('members', []),
                member_of=data.get('member_of', []),
                superordinates=data.get('superordinates', [])
            )
        else:
            return Concept(
                id=data['id'],
                uri=data.get('uri') if data.get('uri') is not None else self.uri_generator.generate(type='collection', id=data['id']),
                concept_scheme=self.concept_scheme,
                labels=data.get('labels', []),
                notes=data.get('notes', []),
                sources=data.get('sources', []),
                broader=data.get('broader', []),
                narrower=data.get('narrower', []),
                related=data.get('related', []),
                member_of=data.get('member_of', []),
                subordinate_arrays=data.get('subordinate_arrays', []),
                matches=data.get('matches', {})
            )


class SimpleCsvProvider(MemoryProvider):
    '''
    A provider that reads a simple csv format into memory.

    The supported csv format looks like this:
    <id>,<preflabel>,<note>,<source>

    This provider essentialy provides a flat list of concepts. This is commonly
    associated with short lookup-lists.

    .. versionadded:: 0.2.0
    '''

    def __init__(self, metadata, reader, **kwargs):
        '''
        :param metadata: A metadata dictionary.
        :param reader: A csv reader.
        '''
        super(SimpleCsvProvider, self).__init__(metadata, [], **kwargs)
        self.list = [self._from_row(row) for row in reader]

    def _from_row(self, row):
        id = row[0]
        labels = [{'label': row[1], 'type':'prefLabel'}]
        if len(row) > 2 and row[2]:
            notes = [{'note': row[2], 'type':'note'}]
        else:
            notes = []
        if len(row) > 3 and row[3]:
            sources = [{'citation': 'My citation.'}]
        else:
            sources = []
        return Concept(
            id=id,
            uri=self.uri_generator.generate(type='concept', id=id),
            labels=labels,
            notes=notes,
            sources=sources
        )
