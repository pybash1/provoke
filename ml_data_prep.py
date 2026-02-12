# Backward compatibility shim - moved to provoke.ml.data_prep
from provoke.ml.data_prep import (
    augment_from_rejected_urls,
    create_fasttext_training_file,
    export_indexed_pages,
    fetch_basic_info,
    fetch_page_content,
    split_training_data,
)

__all__ = [
    "augment_from_rejected_urls",
    "create_fasttext_training_file",
    "export_indexed_pages",
    "fetch_basic_info",
    "fetch_page_content",
    "split_training_data",
]
