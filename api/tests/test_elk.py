# This module is meant to test so that functionalities within the
# ELK part of the GPT-3 project is working as intended without crashing.

from es.elastic import LingtelliElastic
from settings.settings import TIIP_CSV_DIR
from api.data.importer import CSVLoader
from api.params.definitions import SearchDocument, SearchField


class TestELK:

    client = LingtelliElastic()

    def test_answer():
        # Test a normal answer from Chat-GPT.
        return

    def test_index(self):
        self.index = 'random-test-index'
        self.mappings = {
            "content": {"type": "text"}
        }
        assert self.client.index_exists(self.index) == False
        self.client._create_index(
            self.index, 'content', mappings=self.mappings)
        assert self.client.index_exists(self.index) == True
        self.client.delete_index(self.index)
        assert self.client.index_exists(self.index) == False

    def test_delete_source(self):
        # Test deleting documents from a specific source (file)
        self.index = 'test-del-source-index'
        self.mappings = {
            "content": {"type": "text"}
        }
        self.source = '通用.csv'

        csv_object = CSVLoader(self.index, TIIP_CSV_DIR + '/' + self.source)
        csv_object.save_bulk()
        del csv_object
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

    def test_QA(self):
        # Test a '-qa' index and check for answers.
        return

    def test_question(self):
        # Test a normal question to Chat-GPT
        return
