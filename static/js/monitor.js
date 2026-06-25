$(function() {
  const online = {};
  const offline = {};

  function updateStats() {
    let on = 0, off = 0;
    for (const id in online) { if (online[id]) on++; else off++; }
    for (const id in offline) { if (offline[id]) off++; }
    $('#onlineCount').text(on || '—');
    $('#offlineCount').text(off || '—');
  }

  $('.live-monitor-card').each(function() {
    const serverId = $(this).data('server-id');
    if (!serverId) return;

    const socket = io('/monitor', {
      query: { server_id: serverId },
      transports: ['websocket', 'polling'],
    });

    socket.on('stats', function(info) {
      const sid = serverId;
      $('#cpu' + sid).text(info.cpu || '--');
      $('#mem' + sid).text(info.mem || '--');
      $('#disk' + sid).text(info.disk || '--');
      $('#monOs' + sid).text((info.os || '?').toUpperCase());

      $('#cpuBar' + sid).css('width', Math.min(parseFloat(info.cpu) || 0, 100) + '%');
      $('#memBar' + sid).css('width', Math.min(parseFloat(info.mem) || 0, 100) + '%');
      $('#diskBar' + sid).css('width', Math.min(parseFloat(info.disk) || 0, 100) + '%');

      online[sid] = true; offline[sid] = false;
      updateStats();
    });

    socket.on('error', function() {
      offline[serverId] = true; online[serverId] = false;
      updateStats();
    });
  });

  window.openMonitorDetail = function(sid) { window.location.href = '/terminal/' + sid; };
});
