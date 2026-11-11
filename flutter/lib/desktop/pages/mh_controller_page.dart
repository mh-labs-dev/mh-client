import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_hbb/common.dart';
import 'package:flutter_hbb/common/hbbs/hbbs.dart';
import 'package:flutter_hbb/common/widgets/login.dart';
import 'package:flutter_hbb/consts.dart';
import 'package:flutter_hbb/models/platform_model.dart';
import 'package:flutter_hbb/utils/http_service.dart' as http;
import 'package:get/get.dart';

import 'desktop_setting_page.dart';

List<PeerPayload> mhAccessibleMacs(Map<String, dynamic> data) {
  if (data['error'] != null) throw FormatException(data['error'].toString());
  if (data['data'] is! List || data['total'] is! num) {
    throw const FormatException('服务器返回了无法识别的设备列表。');
  }
  return (data['data'] as List)
      .map((item) => PeerPayload.fromJson(item))
      .where((peer) => PeerPayload.toPeer(peer).platform == kPeerPlatformMacOS)
      .toList();
}

/// Controller preview: account authentication and accessible devices only.
class MhControllerPage extends StatefulWidget {
  const MhControllerPage({super.key});

  @override
  State<MhControllerPage> createState() => _MhControllerPageState();
}

class _MhControllerPageState extends State<MhControllerPage> {
  final _username = TextEditingController();
  final _password = TextEditingController();
  bool _signedIn = false;
  bool _busy = false;
  String _error = '';
  List<PeerPayload> _devices = [];

  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!isMhControllerConfigured) return;
    if (_busy) return;
    if (_username.text.trim().isEmpty || _password.text.isEmpty) {
      setState(() => _error = '请输入用户名和密码。');
      return;
    }
    setState(() {
      _busy = true;
      _error = '';
    });
    try {
      final response = await gFFI.userModel
          .login(LoginRequest(
            username: _username.text.trim(),
            password: _password.text,
            id: await bind.mainGetMyId(),
            uuid: await bind.mainGetUuid(),
            autoLogin: true,
            type: HttpType.kAuthReqTypeAccount,
          ))
          .timeout(const Duration(seconds: 20));
      if (response.type == HttpType.kAuthResTypeToken &&
          response.access_token != null &&
          response.user != null) {
        await bind.mainSetLocalOption(
            key: 'access_token', value: response.access_token!);
        await bind.mainSetLocalOption(
            key: 'user_info', value: jsonEncode(response.user));
      } else if (response.type == HttpType.kAuthResTypeEmailCheck) {
        final verified = await verificationCodeDialog(
            response.user,
            response.secret,
            response.tfa_type != HttpType.kAuthResTypeTfaCheck);
        if (verified != true) return;
      } else {
        throw Exception('登录未完成，请检查账号状态。');
      }
      if (!mounted) return;
      _password.clear();
      setState(() => _signedIn = true);
      await _loadDevices();
    } catch (error) {
      if (mounted) setState(() => _error = '登录失败：$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _loadDevices() async {
    setState(() {
      _busy = true;
      _error = '';
      _devices = [];
    });
    try {
      final api = await bind.mainGetApiServer();
      final devices = <PeerPayload>[];
      int page = 1;
      int total = 0;
      do {
        final uri = Uri.parse('$api/api/peers').replace(queryParameters: {
          'current': '$page',
          'pageSize': '100',
          'accessible': '',
          'status': '1',
        });
        final response = await http
            .get(uri, headers: getHttpHeaders())
            .timeout(const Duration(seconds: 20));
        if (response.statusCode == 401) {
          await gFFI.userModel.reset(resetOther: true);
          if (mounted) setState(() => _signedIn = false);
          throw Exception('登录已失效，请重新登录。');
        }
        if (response.statusCode != 200) {
          throw Exception('HTTP ${response.statusCode}');
        }
        final data =
            jsonDecode(decode_http_response(response)) as Map<String, dynamic>;
        devices.addAll(mhAccessibleMacs(data));
        total = (data['total'] as num).toInt();
        page++;
      } while ((page - 1) * 100 < total);
      if (mounted) setState(() => _devices = devices);
    } catch (error) {
      if (mounted) setState(() => _error = '设备列表读取失败：$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _logout() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _devices = [];
    });
    await gFFI.userModel.logOut();
    if (mounted) {
      setState(() {
        _signedIn = false;
        _busy = false;
        _error = '';
      });
    }
  }

  @override
  Widget build(BuildContext context) => Obx(() {
        final accountLoggedIn = gFFI.userModel.isLogin;
        final loggedIn = _signedIn && accountLoggedIn;
        return Column(children: [
          Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
              child: Row(children: [
                const Text('MH',
                    style:
                        TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                const Spacer(),
                if (loggedIn)
                  TextButton(
                      onPressed: _busy ? null : _logout,
                      child: const Text('退出登录')),
                TextButton.icon(
                    onPressed: _busy
                        ? null
                        : () {
                            DesktopSettingPage.switch2page(
                                DesktopSettingPage.tabKeys.first);
                          },
                    icon: const Icon(Icons.settings_outlined, size: 18),
                    label: const Text('设置')),
              ])),
          const Divider(height: 1),
          if (_busy) const LinearProgressIndicator(),
          Expanded(
              child: Center(
                  child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620),
            child: ListView(
                shrinkWrap: true,
                padding: const EdgeInsets.all(32),
                children: [
                  if (loggedIn) ...[
                    const Text('我的 Mac',
                        style: TextStyle(fontSize: 30, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 12),
                    Text(gFFI.userModel.displayNameOrUserName),
                    const SizedBox(height: 28),
                  ],
                  if (!loggedIn) ...[
                    if (!isMhControllerConfigured) ...[
                      const Text('服务配置待就绪，暂不可登录。'),
                      const SizedBox(height: 16),
                    ],
                    TextField(
                        controller: _username,
                        enabled: !_busy && isMhControllerConfigured,
                        autofocus: true,
                        decoration: const InputDecoration(
                            labelText: '用户名', border: OutlineInputBorder()),
                        textInputAction: TextInputAction.next),
                    const SizedBox(height: 16),
                    TextField(
                        controller: _password,
                        enabled: !_busy && isMhControllerConfigured,
                        obscureText: true,
                        decoration: const InputDecoration(
                            labelText: '密码', border: OutlineInputBorder()),
                        onSubmitted: (_) => _login()),
                    const SizedBox(height: 24),
                    SizedBox(
                        height: 50,
                        child: ElevatedButton(
                            onPressed: _busy || !isMhControllerConfigured
                                ? null
                                : _login,
                            child: Text(_busy ? '正在登录…' : '登录',
                                style: const TextStyle(fontSize: 18)))),
                  ] else ...[
                    if (!_busy && _devices.isEmpty && _error.isEmpty)
                      const Text('暂无可用 Mac'),
                    for (final device in _devices)
                      Card(
                          child: Padding(
                              padding: const EdgeInsets.all(20),
                              child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    const Icon(Icons.desktop_mac, size: 40),
                                    const SizedBox(height: 12),
                                    Text(
                                        device.info['device_name']
                                                ?.toString() ??
                                            'Mac',
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                            fontSize: 22,
                                            fontWeight: FontWeight.w600)),
                                    const SizedBox(height: 20),
                                    SizedBox(
                                        height: 52,
                                        child: ElevatedButton.icon(
                                            onPressed: _busy
                                                ? null
                                                : () =>
                                                    connect(context, device.id),
                                            icon: const Icon(Icons.open_in_new),
                                            label: const Text('连接 Mac',
                                                style:
                                                    TextStyle(fontSize: 18)))),
                                  ]))),
                    const SizedBox(height: 12),
                    TextButton.icon(
                        onPressed: _busy ? null : _loadDevices,
                        icon: const Icon(Icons.refresh),
                        label: const Text('刷新设备列表')),
                  ],
                  if (_error.isNotEmpty)
                    Padding(
                        padding: const EdgeInsets.only(top: 18),
                        child: Text(_error,
                            style: TextStyle(
                                color: Theme.of(context).colorScheme.error))),
                ]),
          ))),
        ]);
      });
}
