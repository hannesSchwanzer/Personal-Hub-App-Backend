from meilisearch.errors import MeilisearchApiError


from app.search.client import client
from app.search.indices import FOODS_INDEX
from app.search.settings import (
    FOODS_SEARCHABLE_ATTRIBUTES,
    FOODS_FILTERABLE_ATTRIBUTES,
    FOODS_SORTABLE_ATTRIBUTES,
    FOODS_CUSTOM_RANKING,
)


def setup_foods_index():
    try:
        index = client.get_index(FOODS_INDEX)

    except MeilisearchApiError:
        task = client.create_index(
            uid=FOODS_INDEX,
            options={"primaryKey": "id"},
        )

        client.wait_for_task(task.task_uid)

        index = client.get_index(FOODS_INDEX)

    index.update_searchable_attributes(
        FOODS_SEARCHABLE_ATTRIBUTES
    )

    index.update_filterable_attributes(
        FOODS_FILTERABLE_ATTRIBUTES
    )

    index.update_sortable_attributes(
        FOODS_SORTABLE_ATTRIBUTES
    )

    index.update_ranking_rules(
        FOODS_CUSTOM_RANKING
    )

    return index
