# Copyright (C) 2022 Ludger Hellerhoff, ludger@cam-ai.de
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

from django.urls import path
from sys import argv
from .views import onecam , onedetector, oneeventer

urlpatterns = [
  path('cam/<int:camnr>/', onecam, name='onecam'),
  path('cam/<int:camnr>/<int:tokennr>/<str:token>/', onecam, name='onecamtoken'),
  path('detector/<int:detectornr>/', onedetector, name='onedetector'),
  path('detector/<int:detectornr>/<int:tokennr>/<str:token>/', onedetector, name='onedetectortoken'),
  path('eventer/<int:eventernr>/', oneeventer, name='oneeventer'),
  path('eventer/<int:eventernr>/<int:tokennr>/<str:token>/', oneeventer, name='oneeventertoken'),
]
