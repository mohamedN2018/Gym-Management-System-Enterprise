"""Product management service."""

from __future__ import annotations

from collections.abc import Callable

from app.core.base.service import BaseService
from app.core.errors import ConflictError, NotFoundError
from app.core.events import Event, EventBus
from app.core.pagination import Page, PageRequest, Sort
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.inventory.dtos import CreateProductRequest, ProductDTO, to_product_dto
from app.modules.inventory.events import InventoryEvents
from app.modules.inventory.models.product import Product
from app.modules.inventory.repositories import ProductRepository
from app.modules.inventory.validators import CreateProductValidator

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


class ProductService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None, events=events)
        self._uow_factory = uow_factory
        self._validator = CreateProductValidator()

    def create_product(
        self, request: CreateProductRequest, *, created_by: int | None = None
    ) -> Result[ProductDTO]:
        def _create() -> ProductDTO:
            self._validator.validate_and_raise(request)
            with self._uow_factory() as uow:
                repo = ProductRepository(uow.session)
                sku = (request.sku or "").strip() or f"P{repo.count(include_deleted=True) + 1:04d}"
                if repo.find_by_sku(sku) is not None:
                    raise ConflictError("Product SKU already exists.", details={"sku": sku})
                product = Product(
                    sku=sku,
                    name=request.name.strip(),
                    price=request.price,
                    stock_quantity=request.stock_quantity,
                    category=(request.category or None),
                    barcode=(request.barcode or None),
                    created_by=created_by,
                )
                repo.add(product)
                dto = to_product_dto(product)
                uow.commit()
            self._publish(Event(InventoryEvents.PRODUCT_CREATED, {"product_id": dto.id}))
            return dto

        return self._guard(_create, message="Could not create product")

    def list_products(self, request: PageRequest | None = None) -> Result[Page[ProductDTO]]:
        def _list() -> Page[ProductDTO]:
            with self._uow_factory() as uow:
                page = ProductRepository(uow.session).list(
                    request or PageRequest(sort=(Sort.asc("name"),))
                )
                return Page(
                    items=[to_product_dto(p) for p in page.items],
                    total=page.total,
                    page=page.page,
                    size=page.size,
                )

        return self._guard(_list, message="Could not list products")

    def adjust_stock(
        self, product_id: int, delta: int, *, updated_by: int | None = None
    ) -> Result[ProductDTO]:
        def _adjust() -> ProductDTO:
            with self._uow_factory() as uow:
                repo = ProductRepository(uow.session)
                product = repo.get(product_id)
                if product is None:
                    raise NotFoundError("Product not found.", details={"product_id": product_id})
                product.stock_quantity = max(0, product.stock_quantity + delta)
                product.updated_by = updated_by
                repo.update(product)
                dto = to_product_dto(product)
                uow.commit()
            return dto

        return self._guard(_adjust, message="Could not adjust stock")
