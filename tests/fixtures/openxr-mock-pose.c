/* Test-only pose source for Unity's Windows mock runtime. Never copied to a player package. */
#define WIN32_LEAN_AND_MEAN
#define XR_NO_PROTOTYPES
#include <windows.h>
#include <string.h>
#include "openxr_loader_negotiation.h"

static PFN_xrGetInstanceProcAddr mockGetProc;
static PFN_xrCreateReferenceSpace mockCreateReferenceSpace;
static PFN_xrCreateActionSpace mockCreateActionSpace;
static PFN_xrLocateSpace mockLocateSpace;
static PFN_xrLocateViews mockLocateViews;
static XrSpace headSpace;
static XrSpace actionSpaces[64];
static unsigned actionSpaceCount;
static wchar_t trackingLossFile[32768];
static volatile LONG observedTrackingLoss;

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
    if (strcmp(name, "xrCreateReferenceSpace") == 0) {
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
