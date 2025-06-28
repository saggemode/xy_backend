from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import Cart
from product.models import Product, ProductVariant
from store.models import Store
from decimal import Decimal
import uuid

User = get_user_model()

class CartModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.store = Store.objects.create(
            name='Test Store',
            description='Test store description',
            status='active'
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='Test product description',
            price=Decimal('29.99'),
            stock=10,
            store=self.store
        )
        self.variant = ProductVariant.objects.create(
            name='Test Variant',
            price=Decimal('34.99'),
            stock=5,
            product=self.product
        )

    def test_cart_creation(self):
        cart = Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=2
        )
        self.assertEqual(cart.user, self.user)
        self.assertEqual(cart.store, self.store)
        self.assertEqual(cart.product, self.product)
        self.assertEqual(cart.quantity, 2)
        self.assertFalse(cart.is_deleted)

    def test_cart_with_variant(self):
        cart = Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            variant=self.variant,
            quantity=1
        )
        self.assertEqual(cart.variant, self.variant)
        self.assertEqual(cart.unit_price, self.variant.current_price)

    def test_cart_total_price(self):
        cart = Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=3
        )
        expected_total = self.product.current_price * 3
        self.assertEqual(cart.total_price, expected_total)

    def test_cart_soft_delete(self):
        cart = Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=1
        )
        cart.soft_delete(user=self.user)
        self.assertTrue(cart.is_deleted)
        self.assertIsNotNone(cart.deleted_at)

    def test_cart_restore(self):
        cart = Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=1
        )
        cart.soft_delete(user=self.user)
        cart.restore(user=self.user)
        self.assertFalse(cart.is_deleted)
        self.assertIsNone(cart.deleted_at)

    def test_cart_validation_quantity(self):
        with self.assertRaises(Exception):
            cart = Cart(
                user=self.user,
                store=self.store,
                product=self.product,
                quantity=0
            )
            cart.full_clean()

    def test_cart_validation_stock(self):
        with self.assertRaises(Exception):
            cart = Cart(
                user=self.user,
                store=self.store,
                product=self.product,
                quantity=15  # More than available stock
            )
            cart.full_clean()

    def test_cart_class_methods(self):
        Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=2
        )
        Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            variant=self.variant,
            quantity=1
        )

        user_cart = Cart.get_user_cart(self.user)
        self.assertEqual(user_cart.count(), 2)

        total = Cart.get_cart_total(self.user)
        expected_total = (self.product.current_price * 2) + self.variant.current_price
        self.assertEqual(total, expected_total)

        count = Cart.get_cart_count(self.user)
        self.assertEqual(count, 3)

class CartAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.store = Store.objects.create(
            name='Test Store',
            description='Test store description',
            status='active'
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='Test product description',
            price=Decimal('29.99'),
            stock=10,
            store=self.store
        )
        self.variant = ProductVariant.objects.create(
            name='Test Variant',
            price=Decimal('34.99'),
            stock=5,
            product=self.product
        )
        self.client.force_authenticate(user=self.user)

    def test_list_cart_items(self):
        Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=2
        )
        
        url = reverse('cart-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['quantity'], 2)

    def test_create_cart_item(self):
        url = reverse('cart-list')
        data = {
            'product_id': str(self.product.id),
            'store_id': str(self.store.id),
            'quantity': 3,
            'selected_size': 'M',
            'selected_color': 'Blue'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Cart.objects.count(), 1)
        cart_item = Cart.objects.first()
        self.assertEqual(cart_item.quantity, 3)
        self.assertEqual(cart_item.selected_size, 'M')

    def test_create_cart_item_with_variant(self):
        url = reverse('cart-list')
        data = {
            'product_id': str(self.product.id),
            'store_id': str(self.store.id),
            'variant_id': str(self.variant.id),
            'quantity': 2
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cart_item = Cart.objects.first()
        self.assertEqual(cart_item.variant, self.variant)

    def test_update_cart_item(self):
        cart_item = Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=1
        )
        
        url = reverse('cart-detail', args=[cart_item.id])
        data = {'quantity': 5}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 5)

    def test_delete_cart_item(self):
        cart_item = Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=1
        )
        
        url = reverse('cart-detail', args=[cart_item.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        cart_item.refresh_from_db()
        self.assertTrue(cart_item.is_deleted)

    def test_cart_summary(self):
        Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=2
        )
        Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            variant=self.variant,
            quantity=1
        )
        
        url = reverse('cart-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_items'], 3)
        expected_total = (self.product.current_price * 2) + self.variant.current_price
        self.assertEqual(response.data['total_price'], expected_total)

    def test_add_item_action(self):
        url = reverse('cart-add-item')
        data = {
            'product_id': str(self.product.id),
            'store_id': str(self.store.id),
            'quantity': 2
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Cart.objects.count(), 1)

    def test_clear_cart(self):
        Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=1
        )
        
        url = reverse('cart-clear')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Cart.objects.filter(is_deleted=False).count(), 0)

    def test_cart_count(self):
        Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=3
        )
        
        url = reverse('cart-count')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_quantity'], 3)
        self.assertEqual(response.data['item_count'], 1)

    def test_search_cart(self):
        Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=1
        )
        
        url = reverse('cart-search')
        response = self.client.get(url, {'q': 'Test Product'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_validate_stock(self):
        Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=15  # More than available stock
        )
        
        url = reverse('cart-validate-stock')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertFalse(response.data[0]['is_available'])

    def test_bulk_update(self):
        cart_item1 = Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            quantity=1
        )
        cart_item2 = Cart.objects.create(
            user=self.user,
            store=self.store,
            product=self.product,
            variant=self.variant,
            quantity=2
        )
        
        url = reverse('cart-bulk-update')
        data = {
            'updates': [
                {'cart_id': str(cart_item1.id), 'quantity': 5},
                {'cart_id': str(cart_item2.id), 'quantity': 3}
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_item1.refresh_from_db()
        cart_item2.refresh_from_db()
        self.assertEqual(cart_item1.quantity, 5)
        self.assertEqual(cart_item2.quantity, 3)

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=None)
        url = reverse('cart-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_product_id(self):
        url = reverse('cart-list')
        data = {
            'product_id': str(uuid.uuid4()),  # Non-existent product
            'store_id': str(self.store.id),
            'quantity': 1
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_insufficient_stock(self):
        url = reverse('cart-list')
        data = {
            'product_id': str(self.product.id),
            'store_id': str(self.store.id),
            'quantity': 15  # More than available stock
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
