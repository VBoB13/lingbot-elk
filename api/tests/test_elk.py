# This module is meant to test so that functionalities within the
# ELK part of the GPT-3 project is working as intended without crashing.
import time

from es.elastic import LingtelliElastic
from settings.settings import TIIP_CSV_DIR
from data.importer import CSVLoader
from params.definitions import SearchDocument, SearchField


class TestELK:

    index = 'random-test-index'
    mappings = {
        "content": {"type": "text"}
    }

    def test_index_create_delete(self):
        self.client = LingtelliElastic()
        assert self.client.index_exists(self.index) == False
        try:
            self.client._create_index(
                self.index, 'content', language='CH', mappings=self.mappings)
        except Exception as err:
            raise AssertionError('Index could NOT be created...') from err

        else:
            time.sleep(2)
            self.client.update_index({'vendor_id': self.index})
            assert self.client.index_exists(self.index) == True
            self.client.delete_index(self.index)
            time.sleep(2)
            assert self.client.index_exists(self.index) == False

    def test_delete_source(self):
        # Test deleting documents from a specific source (file)
        self.client = LingtelliElastic()
        self.index = 'test-del-source-index'
        self.source = '通用.csv'

        csv_object = CSVLoader(self.index, TIIP_CSV_DIR + '/' + self.source)
        csv_object.save_bulk()
        assert self.client.index_exists(self.index) == True
        self.doc = SearchDocument(
            vendor_id=self.index,
            match=SearchField(
                name='source',
                search_term=self.source,
                operator='AND',
                min_should_match=1))

        results = self.client.search(self.doc)
        assert len(results["hits"]) > 0

        self.client.delete_by_query(index=self.index, query={
                                    "match": {"source": self.source}})

        results = self.client.search(self.doc)
        assert len(results["hits"]) == 0
        self.client.delete_index(self.index)
        assert self.client.index_exists(self.index) == False
