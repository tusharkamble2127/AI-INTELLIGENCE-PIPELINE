from datetime import datetime, timezone

from src.models.entities import (
    PricingModel,
    ProductEntity,
    Source,
)


def test_product_entity():
    product = ProductEntity(
        source=Source(
            name="Test Source",
            url="https://example.com"
        ),
        startup_name="Example AI",
        pricing_model=PricingModel.FREEMIUM,
        collected_at=datetime.now(timezone.utc),
    )

    assert product.record_type.value == "PRODUCT"
    assert product.pricing_model.value == "FREEMIUM"