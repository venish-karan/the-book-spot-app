from os import name
from django.urls import path

from . import views

urlpatterns = [
    path('', views.store, name="store"),
    path('cart/', views.cart, name="cart"),
    path('checkout/', views.checkout, name="checkout"),
    path('update_item/', views.updateItem, name="update_item"),
    path('process_order/', views.processOrder, name="process_order"),
    path('login/', views.loginPage, name="loginPage"),
    path('logout/', views.logoutUser, name="logoutUser"),
    path('register/', views.registerPage, name="registerPage"),
    path('search', views.search, name="search"),
    path('track_order', views.track_order, name="track_order"),
    path('seller/', views.seller, name="seller"),
    path('profile/', views.profile, name="profile"),
    path('success', views.success, name="success"),
    path('update_profile', views.update_profile, name="update_profile"),
    path('product_view/', views.product_view, name="product_view"),
    ]