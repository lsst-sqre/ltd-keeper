"""Generate Jinja template rendering context from domain models."""

from __future__ import annotations

from collections import UserList
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

from keeper.models import Build, Edition, EditionKind, Product


@dataclass
class ProjectContext:
    """Template context model for a project."""

    title: str
    """Project title."""

    source_repo_url: str
    """Url of the associated GitHub repository."""

    url: str
    """Root URL where this project is published."""

    @classmethod
    def from_product(cls, product: Product) -> ProjectContext:
        return cls(
            title=product.title,
            source_repo_url=product.doc_repo,
            url=product.published_url,
        )


@dataclass
class EditionContext:
    """Template context model for an edition."""

    title: str
    """Human-readable label for this edition."""

    url: str
    """URL where this edition is published."""

    date_updated: datetime
    """Date when this edition was last updated."""

    kind: EditionKind
    """The edition's kind."""

    slug: str
    """The edition's slug."""

    git_ref: Optional[str]
    """The git ref that this edition tracks."""

    github_url: Optional[str]
    """URL to this git ref on GitHub."""

    @classmethod
    def from_edition(
        cls, edition: Edition, product: Product
    ) -> EditionContext:
        if edition.tracked_ref and product.doc_repo:
            repo_url = product.doc_repo.rstrip("/")
            if repo_url[-4:] == ".git":
                repo_url = repo_url[:-4]
            github_url = f"{repo_url}/tree/{edition.tracked_ref}"
        else:
            github_url = None

        return cls(
            title=edition.title,
            url=edition.published_url,
            date_updated=edition.date_rebuilt,
            kind=edition.kind,
            slug=edition.slug,
            git_ref=edition.tracked_ref,
            github_url=github_url,
        )


class EditionContextList(UserList):
    def __init__(self, contexts: Sequence[EditionContext]) -> None:
        self.data: List[EditionContext] = list(contexts)
        self.data.sort(key=lambda x: x.date_updated)

    @property
    def main_edition(self) -> EditionContext:
        """The main (current) edition."""
        for edition in self.data:
            if edition.slug == "__main":
                return edition
        raise ValueError("No __main edition found")

    @property
    def has_releases(self) -> bool:
        return len(self.releases) > 0

    @property
    def releases(self) -> List[EditionContext]:
        """All editions tagged as releases."""
        release_kinds = (
            EditionKind.release,
            EditionKind.major,
            EditionKind.minor,
        )
        release_items = [
            e
            for e in self.data
            if (e.kind in release_kinds and e.slug != "__main")
        ]
        sorted_items = sorted(
            release_items, key=lambda x: x.slug, reverse=True
        )
        return sorted_items

    @property
    def has_drafts(self) -> bool:
        return len(self.drafts) > 0

    @property
    def drafts(self) -> List[EditionContext]:
        """All editions tagged as drafts."""
        draft_items = [
            e
            for e in self.data
            if (e.kind == EditionKind.draft and e.slug != "__main")
        ]
        return sorted(draft_items, key=lambda x: x.date_updated, reverse=True)


@dataclass
class BuildContext:
    """Template context model for a build."""

    slug: str
    """The URL slug for this build."""

    url: str
    """The URL for this build."""

    git_ref: Optional[str]
    """The git ref associated with this build (if appropriate."""

    date: datetime
    """Date when the build was uploaded."""

    @classmethod
    def from_build(cls, build: Build) -> BuildContext:
        return cls(
            slug=build.slug,
            url=build.published_url,
            git_ref=build.git_ref,
            date=build.date_created,
        )


class BuildContextList(UserList):
    def __init__(self, contexts: Sequence[BuildContext]) -> None:
        self.data: List[BuildContext] = list(contexts)
        self.data.sort(key=lambda x: x.date)


@dataclass
class Context:
    """A class that creates Jinja template rendering context from
    domain models.
    """

    project_context: ProjectContext

    edition_contexts: EditionContextList

    build_contexts: BuildContextList

    @classmethod
    def create(cls, product: Product) -> Context:
        project_context = ProjectContext.from_product(product)

        edition_contexts: EditionContextList = EditionContextList(
            [
                EditionContext.from_edition(edition=edition, product=product)
                for edition in product.editions
            ]
        )

        build_contexts: BuildContextList = BuildContextList(
            [BuildContext.from_build(build) for build in product.builds]
        )

        return cls(
            project_context=project_context,
            edition_contexts=edition_contexts,
            build_contexts=build_contexts,
        )
