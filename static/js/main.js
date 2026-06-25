$(function() {

  $('.test-server').on('click', function() {
    const $btn = $(this);
    const id = $btn.data('id');
    const $row = $btn.closest('tr');
    const $status = $row.find('.status-badge');

    $status.removeClass().addClass('status-badge status-unknown').text('Testing...');
    $btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i>');

    $.post('/api/servers/' + id + '/test', function(res) {
      $status.removeClass()
        .addClass('status-badge ' + (res.status === 'online' ? 'status-online' : 'status-offline'))
        .text(res.status === 'online' ? 'Online' : 'Offline');
      if (res.status === 'online') toast(res.message, 'success');
      else toast('Connection failed: ' + (res.message || 'Unknown error'), 'danger');
    }).fail(function() {
      $status.removeClass().addClass('status-badge status-offline').text('Error');
      toast('Connection test failed', 'danger');
    }).always(function() {
      $btn.prop('disabled', false).html('<i class="fas fa-plug"></i>');
    });
  });

  $('.delete-server').on('click', function() {
    const $btn = $(this);
    const id = $btn.data('id');
    if (!confirm('Are you sure you want to delete this server?')) return;
    $.ajax({ url: '/api/servers/' + id, method: 'DELETE', success: function() {
      $btn.closest('tr').fadeOut(300, function() { $(this).remove(); });
      toast('Server deleted', 'success');
    }}).fail(function() { toast('Failed to delete server', 'danger'); });
  });

  $('#addServerForm').on('submit', function(e) {
    e.preventDefault();
    const $btn = $(this).find('button[type=submit]');
    $btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-1"></i>Adding...');
    $.post('/api/servers', $(this).serialize(), function(server) {
      toast('Server "' + server.name + '" added successfully!', 'success');
      $('#addServerForm')[0].reset();
      $('#addServerForm input[name=port]').val('22');
      setTimeout(() => window.location.reload(), 800);
    }).fail(function(xhr) {
      const msg = xhr.responseJSON?.error || 'Failed to add server';
      toast(msg, 'danger');
    }).always(function() {
      $btn.prop('disabled', false).html('<i class="fas fa-plus me-1"></i>Add Server');
    });
  });

  $('#addGroupForm').on('submit', function(e) {
    e.preventDefault();
    const name = $(this).find('input[name=name]').val().trim();
    const color = $(this).find('input[name=color]').val();
    if (!name) return;
    $.ajax({ url: '/api/groups', method: 'POST', contentType: 'application/json',
      data: JSON.stringify({name: name, color: color}),
      success: function(g) {
        toast('Group "' + g.name + '" created', 'success');
        window.location.reload();
      },
      error: function(xhr) { toast(xhr.responseJSON?.error || 'Failed', 'danger'); }
    });
  });

  $(document).on('click', '.delete-group', function() {
    const id = $(this).data('id');
    if (!confirm('Delete this group? Servers will be ungrouped.')) return;
    $.ajax({ url: '/api/groups/' + id, method: 'DELETE',
      success: function() { $('#groupRow' + id).fadeOut(300, function() { $(this).remove(); }); toast('Group deleted', 'success'); },
      error: function() { toast('Failed', 'danger'); }
    });
  });

  $('#groupFilter').on('change', function() {
    const val = $(this).val();
    $('#serverTableBody tr').each(function() {
      if (val === 'all') { $(this).show(); return; }
      const gid = $(this).data('group') || 0;
      $(this).toggle(gid == val);
    });
  });

  $(document).on('click', '.edit-server', function() {
    const id = $(this).data('id');
    const gid = $(this).data('group') || '';
    const name = $(this).data('name');
    const newName = prompt('Server name:', name);
    if (newName === null) return;
    const groups = [];
    $('#addServerForm select[name=group_id] option').each(function() {
      if ($(this).val()) groups.push({id: $(this).val(), name: $(this).text()});
    });
    const gOpts = groups.map(g => g.id + ': ' + g.name).join('\n');
    const newGroup = prompt('Group ID (0 for none):\n' + gOpts, gid);
    if (newGroup === null) return;
    $.ajax({ url: '/api/servers/' + id, method: 'PUT', contentType: 'application/json',
      data: JSON.stringify({
        name: newName.trim(),
        group_id: newGroup ? parseInt(newGroup) : null
      }),
      success: function() { toast('Server updated', 'success'); window.location.reload(); },
      error: function(xhr) { toast(xhr.responseJSON?.error || 'Failed', 'danger'); }
    });
  });

  if (window.location.pathname === '/') {
    $('.test-server').each(function() { $(this).trigger('click'); });
  }
});

function toast(message, type) {
  type = type || 'info';
  const icons = { success: 'fa-check-circle', danger: 'fa-times-circle', warning: 'fa-exclamation-circle', info: 'fa-info-circle' };
  const icon = icons[type] || icons.info;
  const $toast = $('<div class="position-fixed bottom-0 end-0 p-3" style="z-index:9999">'
    + '<div class="toast align-items-center text-bg-' + type + ' border-0 show" role="alert">'
    + '<div class="d-flex">'
    + '<div class="toast-body"><i class="fas ' + icon + ' me-2"></i>' + $('<div>').text(message).html() + '</div>'
    + '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>'
    + '</div></div></div>');
  $('body').append($toast);
  setTimeout(() => { $toast.remove(); }, 4000);
}
