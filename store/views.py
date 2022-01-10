from typing import ContextManager
from django.contrib import messages
from django.http.response import HttpResponse
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import json
import datetime
from .models import *
from .utils import cookieCart, cartData, guestOrder

from django.contrib import messages

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

# from django.contrib.auth.forms import UserCreationForm

# from .models import CreateUserForm
# from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.models import User, auth

import razorpay

def registerPage(request):

    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        email = request.POST['email']
        seller_account = request.POST['seller_account']
        if seller_account == 'yes':
            seller_account = True
        else:
            seller_account = False

        if password1 == password2:
            if User.objects.filter(username=username).exists():
                messages.info(request, 'Username already exists')
                return redirect('registerPage')
            elif User.objects.filter(email=email).exists():
               messages.info(request, 'email already exists')
               return redirect('registerPage')

            else:
                user = User.objects.create_user(username=username, password=password1, first_name=first_name, last_name=last_name, email=email)
                user.save()
                c = Customer.objects.create(user=user, name=username, email=email, seller=seller_account)
                c.save()

                
                print('user created')
                return redirect('loginPage')
        else:
            messages.info(request, 'password must match')
            return redirect('registerPage')

    else:
        return render(request, 'store/register.html')

def loginPage(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            username = User.objects.get(username=username)
        except:
            messages.error(request, 'User does not exist')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            # messages.error(request, "User Name or Password does not exists")
            return redirect('loginPage')
    else:
        return render(request, 'store/login.html')

def logoutUser(request):
    logout(request)
    return redirect('/')

def store(request):

    data = cartData(request)

    cartItems = data['cartItems']

    products = Product.objects.all()

    # print(request.user.email)
    context = {'products': products, 'cartItems': cartItems, 'shipping':False}
    return render(request, 'store/store.html', context)

@login_required(login_url="loginPage")
def cart(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items': items, 'order': order, 'cartItems': cartItems, 'shipping':False}
    return render(request, 'store/cart.html', context)
    
@login_required(login_url="loginPage") # redirect to login page ('/login')
def checkout(request):
    order_id = datetime.datetime.now().timestamp()
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    if request.user.is_authenticated:
        customer_name = request.user.customer
        email = Customer.objects.get(name=customer_name).email

    if request.method == "POST":
        
        client = razorpay.Client(auth=("rzp_test_PT3Pc8sZ8I7MzM", "oedq05t6EWIe3fglx0ryQijK"))
        DATA = {    
            "amount": 100,
            "currency": "INR",
            "payment_capture": "1",  
        }
        
        payment = client.order.create(data=DATA)
    
    context = {'items': items, 'order': order, 'cartItems': cartItems, 'shipping':False,'order_id':order_id,"customer_name":customer_name, "email":email}
    return render(request, 'store/checkout.html', context)

def updateItem(request):

    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']
    # print('Action:', action)
    # print('Product:', productId)

    customer = request.user.customer
    product = Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False,)

    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)
    
    if action == 'add':
        orderItem.quantity = (orderItem.quantity + 1)
    elif action == 'remove':
        orderItem.quantity = (orderItem.quantity - 1)
    
    orderItem.save()

    if(orderItem.quantity <= 0):
        orderItem.delete()

    return JsonResponse('Item was added', safe=False)

# @csrf_exempt
def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()

    data = json.loads(request.body)
    # print(data['track'])

    if request.user.is_authenticated:
        customer = request.user.customer
        data = json.loads(request.body)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)


    else:
        print('User is not logged in')
        print('COOKIES:', request.COOKIES)

        customer, order = guestOrder(request, data)
        

    total = float(data['form']['total'])
    order.transaction_id = transaction_id

    if total == order.get_cart_total:
        order.complete = True
    order.save()

    if order.shipping == True:
        ShippingAddress.objects.filter(customer=customer).delete()
        ShippingAddress.objects.create(
            customer=customer,
            order=order,
            address=data['shipping']['address'],
            city=data['shipping']['city'],
            state=data['shipping']['state'],
            zipcode=data['shipping']['zipcode']
        )
        # ShippingAddress.objects.filter(
        #     customer=customer).delete()

    return JsonResponse('Payment complete!', safe=False)

def search(request):

    data = cartData(request)

    cartItems = data['cartItems']
    # query = request.GET.get('query')
    query = request.GET['query']

    if len(query) > 78:
        # create empty query set
        products = Product.objects.none()
    else:
        # products = Product.objects.all()
        products = Product.objects.filter(name__icontains=query)
        # productsName = Product.objects.filter(name__icontains=query)
        # productsDescription = Product.objects.filter(description__icontains=query)
        # products = productsName.union(productsDescription)

    if products.count() == 0:
        messages.error(request, "No Search Results found. Please refine your query")
    context = {'products': products, 'query': query, 'cartItems': cartItems}
    return render(request, 'store/search.html', context)

@login_required(login_url="loginPage")
def track_order(request):
    
    if request.user.is_authenticated:
        data = cartData(request)

        cartItems = data['cartItems']

        customer = request.user.customer
        orders = list(Order.objects.filter(customer=customer, complete=True))
        order_items_num = [i for i in orders]
        # items = order.orderitem_set.all()
        items = []
        for item_num in order_items_num:
            # print(item_num)
            items += OrderItem.objects.filter(order=item_num)

        items = items[::-1]

        # print(items)
        context = {'items': items, 'cartItems': cartItems}
        
        return render(request, 'store/trackOrder.html', context)
    
    else:
        return redirect('loginPage')

@login_required(login_url="loginPage")
def seller(request):

    if request.user.is_authenticated:

        customer = request.user.customer

        try:
            seller = Customer.objects.get(name=customer, seller=True)

        except Customer.DoesNotExist:
            # return redirect('loginPage')
            seller = None

        data = cartData(request)
        cartItems = data['cartItems']
        products = Product.objects.filter(customer=seller)
        products = products[::-1]

        if request.method == 'POST':
            name = request.POST.get('product_name')
            price = request.POST.get('product_price')
            digital = request.POST.get('digital')
            if(digital == 'yes'):
                digital = True
            else:
                digital = False
            image = request.FILES.get('image')
            description = request.POST.get('description')

            Product.objects.create(
                name=name,
                price=price,
                digital=digital,
                image=image,
                description=description,
                customer=seller,
            )

        context = {'cartItems': cartItems, 'seller': seller, 'products': products}
        return render(request, 'store/seller.html', context)

@login_required(login_url="loginPage")
def profile(request):

    if request.user.is_authenticated:

        customer = request.user.customer

        data_items = cartData(request)
        cartItems = data_items['cartItems']

        try:
            shippingAddress = ShippingAddress.objects.get(customer=customer)
            

            

        except:
            # return redirect('loginPage')
            shippingAddress = None
            

           

        try:
            profilePic = Profile.objects.get(customer=customer)
        except:
            profilePic = None

        try:
            address=shippingAddress.address
            city=shippingAddress.city
            state=shippingAddress.state
            zipcode=shippingAddress.zipcode
        except:
            address=None
            city=None
            state=None
            zipcode=None

        
        if(address==None or city==None or state==None or zipcode==None):
            messages.info(request,'your shipping fields are empty.Please Update your Profile')
            return redirect('update_profile')

        if shippingAddress == None :
                p = Profile.objects.create(
                    customer=customer,
                )
                p.save()
                return redirect('update_profile')
                # data = request.POST
                # ShippingAddress.objects.create(
                #     customer=customer,
                #     address=data['address'],
                #     city=data['city'],
                #     state=data['state'],
                #     zipcode=data['zipcode']
                # )

        if request.method == "POST":
            pimage = request.FILES.get('image')
            Profile.objects.filter(customer=customer).delete()
            Profile.objects.create(
                customer=customer,
                image = pimage
            )
            

    context = {'shippingAddress' : shippingAddress, 'profilePic' : profilePic, 'cartItems': cartItems}
    return render(request, 'store/profile.html', context)


@csrf_exempt
def success(request):
    return render(request, "store/success.html")

def update_profile(request):

    data_items = cartData(request)
    cartItems = data_items['cartItems']

    if request.user.is_authenticated:

        customer = request.user.customer

        data = request.POST

        ShippingAddress.objects.filter(
        customer=customer).delete()
        
        ShippingAddress.objects.create(
            customer=customer,
            address=data.get('address', None),
            city=data.get('city', None),
            state=data.get('state', None),
            zipcode=data.get('zipcode', None)
        )


    context={'cartItems': cartItems}
    return render(request, 'store/update_profile.html', context)

def product_view(request):

    data_items = cartData(request)
    cartItems = data_items['cartItems']

    context={'cartItems':cartItems}
    return render(request, 'store/product_view.html', context)