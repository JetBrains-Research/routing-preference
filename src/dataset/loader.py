"""Load issues from HuggingFace datasets."""

from collections.abc import Iterator

from datasets import load_dataset

from ..models import Issue


class IssueDataset:
    """Load and iterate over issues from the HuggingFace dataset."""

    def __init__(self, dataset_name: str, split: str = "test"):
        """Initialize the dataset.

        Args:
            dataset_name: HuggingFace dataset name.
            split: Dataset split to use (default: "test").
        """
        self.dataset_name = dataset_name
        self.split = split
        self._dataset = load_dataset(dataset_name, split=split)

    def __len__(self) -> int:
        return len(self._dataset)

    def __getitem__(self, idx: int) -> Issue:
        row = self._dataset[idx]
        return Issue(
            id=row["id"],
            repo=row["repo"],
            number=row["number"],
            title=row["title"],
            body=row["body"],
            labels=row.get("labels", []),
        )

    def __iter__(self) -> Iterator[Issue]:
        for i in range(len(self)):
            yield self[i]
