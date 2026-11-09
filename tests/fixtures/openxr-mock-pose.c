/* Test-only pose source for Unity's Windows mock runtime. Never copied to a player package. */
#define WIN32_LEAN_AND_MEAN
#define XR_NO_PROTOTYPES
#include <windows.h>
#include <string.h>
#include "openxr_loader_negotiation.h"

static PFN_xrGetInstanceProcAddr mockGetProc;
static PFN_xrCreateInstance mockCreateInstance;
static PFN_xrSyncActions mockSyncActions;
static PFN_xrSetInputDeviceStateBoolEXT mockSetTriggerClick;
static PFN_xrSetInputDeviceStateFloatEXT mockSetTriggerValue;
static PFN_xrCreateReferenceSpace mockCreateReferenceSpace;
static PFN_xrCreateActionSpace mockCreateActionSpace;
static PFN_xrLocateSpace mockLocateSpace;
static PFN_xrLocateViews mockLocateViews;
static XrSpace headSpace;
static XrSpace actionSpaces[64];
static unsigned actionSpaceCount;
static wchar_t trackingLossFile[32768];
static wchar_t triggerCommandFile[32768];
static wchar_t triggerAckFile[32768];
static volatile LONG observedTrackingLoss;
static XrPath rightHand, triggerClick, triggerValue;
static char triggerCommand = '0';
static char lastAcknowledgedCommand, lastAcknowledgedValue;
static ULONGLONG tapDeadline;

static PFN_xrVoidFunction functionFor(XrInstance instance, const char *name)
{
    PFN_xrVoidFunction function = NULL;
    return XR_SUCCEEDED(mockGetProc(instance, name, &function)) ? function : NULL;
}

static XrResult XRAPI_CALL createInstance(const XrInstanceCreateInfo *info, XrInstance *instance)
{
    if (!triggerCommandFile[0])
        return mockCreateInstance(info, instance);
    const char *extensions[64];
    if (info->enabledExtensionCount >= ARRAYSIZE(extensions))
        return XR_ERROR_LIMIT_REACHED;
    XrInstanceCreateInfo fixtureInfo = *info;
    BOOL alreadyEnabled = FALSE;
    for (uint32_t index = 0; index < info->enabledExtensionCount; index++) {
        extensions[index] = info->enabledExtensionNames[index];
        if (strcmp(extensions[index], XR_EXT_CONFORMANCE_AUTOMATION_EXTENSION_NAME) == 0)
            alreadyEnabled = TRUE;
    }
    if (!alreadyEnabled)
        extensions[fixtureInfo.enabledExtensionCount++] = XR_EXT_CONFORMANCE_AUTOMATION_EXTENSION_NAME;
    fixtureInfo.enabledExtensionNames = extensions;
    return mockCreateInstance(&fixtureInfo, instance);
}

static char readTriggerCommand(void)
{
    HANDLE file = CreateFileW(triggerCommandFile, GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return triggerCommand;
    char command = 0;
    DWORD size = 0;
    ReadFile(file, &command, 1, &size, NULL);
    CloseHandle(file);
    return size == 1 && command >= '0' && command <= '2' ? command : triggerCommand;
}

static BOOL acknowledgeTrigger(char command, char value)
{
    if (command == lastAcknowledgedCommand && value == lastAcknowledgedValue)
        return TRUE;
    HANDLE file = CreateFileW(triggerAckFile, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE,
        NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return FALSE;
    const char line[] = {command, ' ', value, '\n'};
    DWORD size = 0;
    BOOL written = WriteFile(file, line, sizeof(line), &size, NULL) && size == sizeof(line);
    CloseHandle(file);
    if (written) {
        lastAcknowledgedCommand = command;
        lastAcknowledgedValue = value;
    }
    return written;
}

static XrResult XRAPI_CALL syncActions(XrSession session, const XrActionsSyncInfo *info)
{
    if (!triggerCommandFile[0])
        return mockSyncActions(session, info);
    if (!rightHand || !triggerClick || !triggerValue || !mockSetTriggerClick || !mockSetTriggerValue)
        return XR_ERROR_RUNTIME_FAILURE;
    char command = readTriggerCommand();
    ULONGLONG now = GetTickCount64();
    if (command == '2' && triggerCommand != '2')
        tapDeadline = now + 100;
    triggerCommand = command;
    BOOL held = command == '1' || (command == '2' && now < tapDeadline);
    if (XR_FAILED(mockSetTriggerClick(session, rightHand, triggerClick, held ? XR_TRUE : XR_FALSE)) ||
        XR_FAILED(mockSetTriggerValue(session, rightHand, triggerValue, held ? 1.0f : 0.0f)))
        return XR_ERROR_RUNTIME_FAILURE;
    XrResult result = mockSyncActions(session, info);
    if (result == XR_SUCCESS && !acknowledgeTrigger(command, held ? '1' : '0'))
        return XR_ERROR_RUNTIME_FAILURE;
    return result;
}

static BOOL handsUntracked(void)
{
    return trackingLossFile[0] && GetFileAttributesW(trackingLossFile) != INVALID_FILE_ATTRIBUTES;
}

static float recoveredOffset(void)
{
    return InterlockedCompareExchange(&observedTrackingLoss, 0, 0) && !handsUntracked() ? 0.2f : 0.0f;
}

static XrResult XRAPI_CALL createReferenceSpace(XrSession session, const XrReferenceSpaceCreateInfo *info, XrSpace *space)
{
    XrResult result = mockCreateReferenceSpace(session, info, space);
    if (XR_SUCCEEDED(result) && info->referenceSpaceType == XR_REFERENCE_SPACE_TYPE_VIEW)
        headSpace = *space;
    return result;
}

static XrResult XRAPI_CALL createActionSpace(XrSession session, const XrActionSpaceCreateInfo *info, XrSpace *space)
{
    XrResult result = mockCreateActionSpace(session, info, space);
    if (XR_SUCCEEDED(result) && actionSpaceCount < sizeof(actionSpaces) / sizeof(actionSpaces[0]))
        actionSpaces[actionSpaceCount++] = *space;
    return result;
}

static XrResult XRAPI_CALL locateSpace(XrSpace space, XrSpace base, XrTime time, XrSpaceLocation *location)
{
    XrResult result = mockLocateSpace(space, base, time, location);
    if (XR_FAILED(result) || !(location->locationFlags & XR_SPACE_LOCATION_POSITION_VALID_BIT))
        return result;
    if (space == headSpace) {
        location->pose.position.x += recoveredOffset();
        location->pose.position.y = 1.65f;
    }
    for (unsigned index = 0; index < actionSpaceCount; index++) {
        if (space == actionSpaces[index]) {
            location->pose.position.y = 1.25f;
            location->pose.position.z = -0.4f;
            if (handsUntracked()) {
                InterlockedExchange(&observedTrackingLoss, 1);
                location->locationFlags &= ~(XR_SPACE_LOCATION_POSITION_TRACKED_BIT | XR_SPACE_LOCATION_ORIENTATION_TRACKED_BIT);
            } else {
                location->pose.position.x += recoveredOffset();
            }
            break;
        }
    }
    return result;
}

static XrResult XRAPI_CALL locateViews(XrSession session, const XrViewLocateInfo *info, XrViewState *state,
                                     uint32_t capacity, uint32_t *count, XrView *views)
{
    XrResult result = mockLocateViews(session, info, state, capacity, count, views);
    if (XR_SUCCEEDED(result) && (state->viewStateFlags & XR_VIEW_STATE_POSITION_VALID_BIT)) {
        float offset = recoveredOffset();
        for (uint32_t index = 0; index < *count && index < capacity; index++) {
            views[index].pose.position.x += offset;
            views[index].pose.position.y = 1.65f;
        }
    }
    return result;
}

static XrResult XRAPI_CALL getProc(XrInstance instance, const char *name, PFN_xrVoidFunction *function)
{
    XrResult result = mockGetProc(instance, name, function);
    if (XR_FAILED(result) || !*function)
        return result;
    if (strcmp(name, "xrCreateInstance") == 0) {
        mockCreateInstance = (PFN_xrCreateInstance)*function;
        *function = (PFN_xrVoidFunction)createInstance;
    } else if (strcmp(name, "xrSyncActions") == 0) {
        mockSyncActions = (PFN_xrSyncActions)*function;
        if (triggerCommandFile[0]) {
            PFN_xrStringToPath toPath = (PFN_xrStringToPath)functionFor(instance, "xrStringToPath");
            mockSetTriggerClick = (PFN_xrSetInputDeviceStateBoolEXT)functionFor(instance, "xrSetInputDeviceStateBoolEXT");
            mockSetTriggerValue = (PFN_xrSetInputDeviceStateFloatEXT)functionFor(instance, "xrSetInputDeviceStateFloatEXT");
            if (!toPath || XR_FAILED(toPath(instance, "/user/hand/right", &rightHand)) ||
                XR_FAILED(toPath(instance, "/user/hand/right/input/trigger/click", &triggerClick)) ||
                XR_FAILED(toPath(instance, "/user/hand/right/input/trigger/value", &triggerValue)))
                return XR_ERROR_RUNTIME_FAILURE;
        }
        *function = (PFN_xrVoidFunction)syncActions;
    } else if (strcmp(name, "xrCreateReferenceSpace") == 0) {
        mockCreateReferenceSpace = (PFN_xrCreateReferenceSpace)*function;
        *function = (PFN_xrVoidFunction)createReferenceSpace;
    } else if (strcmp(name, "xrCreateActionSpace") == 0) {
        mockCreateActionSpace = (PFN_xrCreateActionSpace)*function;
        *function = (PFN_xrVoidFunction)createActionSpace;
    } else if (strcmp(name, "xrLocateSpace") == 0) {
        mockLocateSpace = (PFN_xrLocateSpace)*function;
        *function = (PFN_xrVoidFunction)locateSpace;
    } else if (strcmp(name, "xrLocateViews") == 0) {
        mockLocateViews = (PFN_xrLocateViews)*function;
        *function = (PFN_xrVoidFunction)locateViews;
    }
    return result;
}

__declspec(dllexport) XrResult XRAPI_CALL xrNegotiateLoaderRuntimeInterface(
    const XrNegotiateLoaderInfo *info, XrNegotiateRuntimeRequest *request)
{
    wchar_t path[32768];
    DWORD length = GetEnvironmentVariableW(L"VR_COMMAND_OPENXR_MOCK_DLL", path, ARRAYSIZE(path));
    if (length == 0 || length >= ARRAYSIZE(path))
        return XR_ERROR_RUNTIME_UNAVAILABLE;
    length = GetEnvironmentVariableW(L"VR_COMMAND_OPENXR_TRACKING_LOSS_FILE", trackingLossFile, ARRAYSIZE(trackingLossFile));
    if (length >= ARRAYSIZE(trackingLossFile))
        return XR_ERROR_RUNTIME_UNAVAILABLE;
    length = GetEnvironmentVariableW(L"VR_COMMAND_OPENXR_TRIGGER_COMMAND", triggerCommandFile, ARRAYSIZE(triggerCommandFile));
    if (length >= ARRAYSIZE(triggerCommandFile))
        return XR_ERROR_RUNTIME_UNAVAILABLE;
    length = GetEnvironmentVariableW(L"VR_COMMAND_OPENXR_TRIGGER_ACK", triggerAckFile, ARRAYSIZE(triggerAckFile));
    if (length >= ARRAYSIZE(triggerAckFile) || (triggerCommandFile[0] && !triggerAckFile[0]))
        return XR_ERROR_RUNTIME_UNAVAILABLE;
    HMODULE runtime = LoadLibraryExW(path, NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!runtime)
        return XR_ERROR_RUNTIME_UNAVAILABLE;
    PFN_xrNegotiateLoaderRuntimeInterface negotiate =
        (PFN_xrNegotiateLoaderRuntimeInterface)GetProcAddress(runtime, "xrNegotiateLoaderRuntimeInterface");
    XrResult result = negotiate ? negotiate(info, request) : XR_ERROR_RUNTIME_UNAVAILABLE;
    if (XR_SUCCEEDED(result)) {
        mockGetProc = request->getInstanceProcAddr;
        request->getInstanceProcAddr = getProc;
    }
    return result;
}
