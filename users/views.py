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

from django.conf import settings
from django.http import HttpResponse, FileResponse
from django_tables2 import SingleTableMixin
from access.c_access import access
from tools.l_tools import djconf
from tf_workers.models import school
from tools.tokens import checktoken
from .filters import archivefilter, myFilterView
from .models import archive as dbarchive
from .tables import archivetable

class archive(SingleTableMixin, myFilterView):
  table_class = archivetable
  queryset = dbarchive.objects.all()
  filterset_class = archivefilter
  paginate_by = 15
  
  def get(self, request, *args, **kwargs):
    self.request = request
    self.schoolnr = kwargs['schoolnr']
    if (((self.schoolnr > 1) or (request.user.is_superuser)) 
        and (access.check('S', self.schoolnr, request.user, 'R'))):
      return(super().get(request, *args, **kwargs))
    else:
      return(HttpResponse('No Access'))


  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context.update({
      'version' : djconf.getconfig('version', 'X.Y.Z'),
      'emulatestatic' : djconf.getconfigbool('emulatestatic', False),
      'debug' : settings.DEBUG,
      'school' : school.objects.get(id=self.schoolnr),
      'user' : self.request.user,
    })
    return context

  def get_template_names(self):
    if self.request.htmx:
      template_name = "users/archive_table_partial.html"
    else:
      template_name = "users/archive_table_htmx.html"
    return template_name
    
def downarchive(request, line_nr, tokennr, token): 
  if checktoken((tokennr, token), 'ADL', line_nr):
    archiveline = dbarchive.objects.get(id = line_nr)
    if archiveline.typecode == 0:
      filename = djconf.getconfig('archivepath', 'data/archive/') + 'frames/' + archiveline.name
    elif archiveline.typecode == 1:
      filename = djconf.getconfig('archivepath', 'data/archive/') + 'videos/' + archiveline.name + '.mp4'
    sourcefile = open(filename, 'rb')
    return FileResponse(sourcefile)
  else:
    return(HttpResponse('No Access.'))
