from es.elastic import LingtelliElastic


def get_mapping() -> dict:
    """
    Function that simply organizes the content generated from
    'elastic_server:9200/_mapping' so that functions can automatically
    detect and work with the correct field.
    """
    es = LingtelliElastic()
    mappings = es.get_mappings()
    final_mapping = {}
    for index in mappings.keys():
        for field in mappings["mappings"]["properties"].keys():
            if mappings["mappings"]["properties"][field]["type"] == "text" \
                    and not mappings["mappings"]["properties"][field].get('index', None):
                final_mapping.update({index: {"context": field}})

    return final_mapping
