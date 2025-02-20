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

from .views import archive, downarchive

urlpatterns = [
	path('archive/<int:schoolnr>/', archive.as_view(), name='archive'),
	path('downarchive/<int:line_nr>/<int:tokennr>/<str:token>/image.bmp', downarchive, name='downmodelbmp'),
	path('downarchive/<int:line_nr>/<int:tokennr>/<str:token>/video.mp4', downarchive, name='downmodelmp4'),
]

