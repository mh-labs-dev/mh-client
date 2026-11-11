import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_hbb/desktop/pages/mh_controller_page.dart';

void main() {
  test('customer list shows only Macs returned by accessible devices API', () {
    final peers = mhAccessibleMacs({
      'total': 3,
      'data': [
        {
          'id': 'mac-a',
          'info': {'os': 'Mac OS / test', 'device_name': 'Mac A'}
        },
        {
          'id': 'win-a',
          'info': {'os': 'Windows / test'}
        },
        {
          'id': 'mac-b',
          'info': {'os': 'macOS / test', 'device_name': 'Mac B'}
        },
      ]
    });
    expect(peers.map((p) => p.id), ['mac-b']);
    expect(peers.single.info['device_name'], 'Mac B');
  });
  test('empty assignment is distinct from denied or malformed API responses',
      () {
    expect(mhAccessibleMacs({'total': 0, 'data': []}), isEmpty);
    expect(() => mhAccessibleMacs({'error': 'denied'}), throwsFormatException);
    expect(() => mhAccessibleMacs({'unexpected': []}), throwsFormatException);
  });
}
